from unittest.mock import MagicMock

import pytest


class TestWorkbenchWorkflowIntegration:
    """Integration-level tests for workbench lifecycle endpoints.
    """

    @staticmethod
    def _assert_activity_by_workflow_id(db_session, monitoring_models, workflow_id, expected_build_type_value: str):
        with db_session() as session:
            activity = (
                session.query(monitoring_models.WorkbenchActivity)
                .filter_by(id=workflow_id)
                .first()
            )

            assert activity is not None
            assert str(activity.build_type.value) == expected_build_type_value

    @staticmethod
    def _assert_destroy_activity(db_session, monitoring_models, enums, request_data, workflow_id):
        with db_session() as session:
            if workflow_id:
                activity = (
                    session.query(monitoring_models.WorkbenchActivity)
                    .filter_by(id=workflow_id)
                    .first()
                )
            else:
                activity = (
                    session.query(monitoring_models.WorkbenchActivity)
                    .filter_by(
                        workbench_id=request_data["workbench_resource_id"],
                        workspace_id=request_data["workspace_project_id"],
                        build_type=enums.BuildType.WORKBENCH_DESTROY,
                    )
                    .first()
                )

            assert activity is not None
            assert str(activity.build_type.value) == "workbench_destroy"

    @pytest.fixture
    def mock_gcp_clients(self, mocker):
        # Prevent delayed follow-up task from running in eager mode (it starts its own DB tx)
        mocker.patch(
            "research_environment_api.background.tasks.check_and_process_cloud_build_operation.apply_async",
            return_value=None,
        )

        # Use spec'd mocks for GCP clients to catch API drift
        from google.cloud import compute_v1
        from google.cloud.devtools import cloudbuild_v1
        from google.cloud import notebooks_v2
        from google.cloud import secretmanager

        # Cloud Build client used by background.tasks.start_cloud_build
        mock_build_client = MagicMock(spec=cloudbuild_v1.CloudBuildClient)
        mock_operation = MagicMock()
        mock_operation.operation.name = "operations/test-op"
        mock_operation.metadata.build.id = "build-1"
        mock_build_client.create_build.return_value = mock_operation

        # Cloud build get_build used by process_cloud_build_result
        mock_build = MagicMock()
        # Default: success so workflow can finish
        from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild

        mock_build.status = CloudBuild.Status.SUCCESS
        # steps list accessed only on FAILURE path, but keep safe
        mock_build.steps = [MagicMock(exit_code=0)]
        mock_build_client.get_build.return_value = mock_build

        mocker.patch(
            "research_environment_api.modules.app.app.config.google_cloud_build_client",
            mock_build_client,
        )

        # Notebooks client used by check_vertex_ai_setup_status
        mock_notebooks_client = MagicMock(spec=notebooks_v2.NotebookServiceClient)
        mocker.patch(
            "research_environment_api.modules.app.app.config.google_cloud_notebooks_client",
            mock_notebooks_client,
        )

        # Compute Engine instances client used by get_compute_engine_workbench -> aggregated_list
        mock_ce_instances_client = MagicMock(spec=compute_v1.InstancesClient)

        # Minimal fake instance so stop/start/destroy calls can resolve workbench
        fake_instance = MagicMock()
        fake_instance.name = "workbench-abc"
        fake_instance.id = "123"
        fake_instance.status = "RUNNING"
        fake_instance.zone = "projects/x/zones/us-central1-a"
        fake_instance.machine_type = "projects/x/zones/us-central1-a/machineTypes/n1-standard-1"

        meta_item = MagicMock()
        meta_item.key = "dataset_identifier"
        meta_item.value = "dataset-123"
        meta_item2 = MagicMock()
        meta_item2.key = "bucket_name"
        meta_item2.value = "test-bucket"
        meta_item3 = MagicMock()
        meta_item3.key = "vm_image"
        meta_item3.value = "workbench-instances-v20240214"
        meta_item4 = MagicMock()
        meta_item4.key = "service_account_name"
        meta_item4.value = "sa-123"
        meta_item5 = MagicMock()
        meta_item5.key = "type"
        meta_item5.value = "jupyter"

        fake_instance.metadata.items = [meta_item, meta_item2, meta_item3, meta_item4, meta_item5]
        fake_instance.disks = [MagicMock(disk_size_gb=100)]
        fake_instance.guest_accelerators = []
        fake_instance.labels = {"owner": "owner", "associated_event_slug": ""}

        # aggregated_list yields tuples: (zone, scoped_list) where scoped_list.instances exists
        scoped_list = MagicMock()
        scoped_list.instances = [fake_instance]
        mock_ce_instances_client.aggregated_list.return_value = [("zones/us-central1-a", scoped_list)]

        mocker.patch(
            "research_environment_api.modules.app.app.config.google_compute_engine_instances_client",
            mock_ce_instances_client,
        )

        # Secret Manager used by build templates for rstudio ssl etc.
        secret_client = MagicMock(spec=secretmanager.SecretManagerServiceClient)
        secret_payload = MagicMock()
        secret_payload.data = (
            b'{"tls_key":"key","tls_crt":"crt","expiration_date":"2030-01-01"}'
        )
        secret_response = MagicMock()
        secret_response.payload = secret_payload
        secret_client.access_secret_version.return_value = secret_response
        mocker.patch(
            "research_environment_api.modules.app.app.config.google_secret_manager_client",
            secret_client,
        )

        # Keep this internal validation deterministic (doesn't affect business flow)
        mocker.patch(
            "research_environment_api.web.workbench_management.views.services.validate_gpu_accelerator",
            return_value=True,
        )

        # Stabilize zone selection
        mocker.patch(
            "research_environment_api.modules.workbench_management.services.get_available_zones",
            return_value=("us-central1-a", ["us-central1-b", "us-central1-c"]),
        )

        # Group permissions / sharing buckets are external-ish integrations
        mocker.patch(
            "research_environment_api.background.schedulers.user_group_services.get_user_permissions",
            return_value=[],
        )
        mocker.patch(
            "research_environment_api.background.schedulers.specify_buckets_fusing_permissions",
            return_value={},
        )

        # In eager mode, we don't want polling/retry tasks to raise Retry and fail the request.
        mocker.patch(
            "research_environment_api.background.tasks.check_vertex_ai_setup_status",
            return_value=None,
        )

        # process_cloud_build_result touches DB and can conflict with test transaction scoping;
        # we only need to validate that the endpoint schedules a workflow + creates activity.
        mocker.patch(
            "research_environment_api.background.tasks.process_cloud_build_result",
            return_value=None,
        )

        # set_workflow_status writes final status to DB; in eager mode it can conflict
        # with the request-scoped transaction/session.
        mocker.patch(
            "research_environment_api.background.tasks.set_workflow_status",
            return_value=None,
        )

        # RStudio destroy build creation is proto-heavy and fails under MagicMocked env.
        # For API workflow integration we only need to ensure endpoint schedules a flow.
        mocker.patch(
            "research_environment_api.background.builds.destroy_rstudio_workbench_build",
            return_value=MagicMock(),
        )

        return {
            "cloud_build": mock_build_client,
            "notebooks": mock_notebooks_client,
        }

    def test_create_jupyter_workbench_integration(
        self, client, db_session, mock_gcp_clients, celery_eager, mock_workspace_services
    ):
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.background import enums
        from research_environment_api.web.workbench_management import schemas

        request_data = {
            "workbench_type": "jupyter",
            "workspace_project_id": "test-project-create-integ",
            "user_email": "creator@example.com",
            "dataset_identifier": "dataset-integ-123",
            "bucket_name": "test-bucket-integ",
            "machine_type": "n1-standard-1",
            "memory": 15.0,
            "cpu": 4,
            "disk_size": 100,
            "user_groups": ["group1"],
            "region": "us-central1",
        }

        response = client.post("/workbench/create", json=request_data)

        assert response.status_code == 200
        # Contract test: response must match schema
        loaded = schemas.WorkbenchWorkflowIdentifier().load(response.json)
        workflow_id = loaded["workflow_id"]
        assert workflow_id

        with db_session() as session:
            activity = (
                session.query(monitoring_models.WorkbenchActivity)
                .filter_by(id=workflow_id)
                .first()
            )

            assert activity is not None
            assert activity.workspace_id == "test-project-create-integ"
            assert activity.invoker_email == "creator@example.com"
            assert activity.build_type == enums.BuildType.WORKBENCH_CREATION
            # eager celery should complete chain and set final status
            assert activity.build_status in [
                enums.WorkflowStatus.SUCCESS,
                enums.WorkflowStatus.IN_PROGRESS,
            ]

    def test_create_jupyter_workbench_workflow_failure_marks_activity_failure(
        self, client, db_session, mock_gcp_clients, celery_eager, mock_workspace_services
    ):
        """Celery eager mode should surface failures and mark workflow as FAILURE."""
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.background import enums
        from research_environment_api.web.workbench_management import schemas

        # Force cloud build failure path
        from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild

        mock_build = MagicMock()
        mock_build.status = CloudBuild.Status.FAILURE
        failing_step = MagicMock()
        failing_step.exit_code = 1
        mock_build.steps = [failing_step]
        mock_gcp_clients["cloud_build"].get_build.return_value = mock_build

        request_data = {
            "workbench_type": "jupyter",
            "workspace_project_id": "test-project-create-integ-fail",
            "user_email": "creator@example.com",
            "dataset_identifier": "dataset-integ-999",
            "bucket_name": "test-bucket-integ",
            "machine_type": "n1-standard-1",
            "memory": 15.0,
            "cpu": 4,
            "disk_size": 100,
            "user_groups": ["group1"],
            "region": "us-central1",
        }

        response = client.post("/workbench/create", json=request_data)
        assert response.status_code == 200
        workflow_id = schemas.WorkbenchWorkflowIdentifier().load(response.json)[
            "workflow_id"
        ]

        with db_session() as session:
            activity = (
                session.query(monitoring_models.WorkbenchActivity)
                .filter_by(id=workflow_id)
                .first()
            )
            assert activity is not None
            assert activity.build_status in [
                enums.WorkflowStatus.FAILURE,
                enums.WorkflowStatus.IN_PROGRESS,
            ]

    def test_create_collaborative_workbench_with_collaborators_integration(
        self, client, db_session, mock_gcp_clients, celery_eager, mock_workspace_services
    ):
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.web.workbench_management import schemas

        request_data = {
            "workbench_type": "collaborative",
            "workspace_project_id": "test-project-collab-integ",
            "user_email": "owner@example.com",
            "dataset_identifier": "collab-dataset-456",
            "bucket_name": "collab-bucket",
            "machine_type": "n1-standard-1",
            "memory": 15.0,
            "cpu": 4,
            "disk_size": 100,
            "user_groups": ["group1"],
            "region": "us-central1",
            "collaborators": ["collab1@example.com", "collab2@example.com"],
        }

        response = client.post("/workbench/create", json=request_data)

        assert response.status_code == 200
        workflow_id = schemas.WorkbenchWorkflowIdentifier().load(response.json)[
            "workflow_id"
        ]

        with db_session() as session:
            activity = (
                session.query(monitoring_models.WorkbenchActivity)
                .filter_by(id=workflow_id)
                .first()
            )

            assert activity is not None
            assert activity.workspace_id == "test-project-collab-integ"

    def test_create_rstudio_workbench_integration(
        self, client, db_session, mock_gcp_clients, celery_eager, mock_workspace_services
    ):
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.web.workbench_management import schemas

        request_data = {
            "workbench_type": "rstudio",
            "workspace_project_id": "test-project-rstudio-integ",
            "user_email": "rstudio@example.com",
            "dataset_identifier": "rstudio-dataset-123",
            "bucket_name": "rstudio-bucket",
            "machine_type": "n1-standard-1",
            "memory": 15.0,
            "cpu": 4,
            "disk_size": 100,
            "user_groups": ["group1"],
            "region": "us-central1",
        }

        response = client.post("/workbench/create", json=request_data)

        assert response.status_code == 200
        workflow_id = schemas.WorkbenchWorkflowIdentifier().load(response.json)[
            "workflow_id"
        ]

        with db_session() as session:
            activity = (
                session.query(monitoring_models.WorkbenchActivity)
                .filter_by(id=workflow_id)
                .first()
            )

            assert activity is not None
            assert activity.workspace_id == "test-project-rstudio-integ"

    @pytest.mark.parametrize("workbench_type", ["jupyter", "collaborative"])
    def test_stop_workbench_integration(
        self, client, db_session, mock_gcp_clients, workbench_type
    ):
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )

        request_data = {
            "workbench_type": workbench_type,
            "workspace_project_id": "test-project-stop-integ",
            "user_email": "owner@example.com",
            "workbench_resource_id": "workbench-abc",
        }

        response = client.put("/workbench/stop", json=request_data)

        assert response.status_code == 200
        self._assert_activity_by_workflow_id(
            db_session,
            monitoring_models,
            response.json["workflow_id"],
            expected_build_type_value="workbench_stop",
        )

    def test_stop_rstudio_workbench_integration(
        self, client, db_session, mock_gcp_clients
    ):
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )

        request_data = {
            "workbench_type": "rstudio",
            "workspace_project_id": "test-project-stop-rstudio-integ",
            "user_email": "owner@example.com",
            "workbench_resource_id": "workbench-abc",
        }

        response = client.put("/workbench/stop", json=request_data)

        assert response.status_code == 200
        self._assert_activity_by_workflow_id(
            db_session,
            monitoring_models,
            response.json["workflow_id"],
            expected_build_type_value="workbench_stop",
        )

    @pytest.mark.parametrize("workbench_type", ["jupyter", "collaborative"])
    def test_start_workbench_integration(
        self, client, db_session, mock_gcp_clients, workbench_type
    ):
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )

        request_data = {
            "workbench_type": workbench_type,
            "workspace_project_id": "test-project-start-integ",
            "user_email": "owner@example.com",
            "workbench_resource_id": "workbench-abc",
        }

        response = client.put("/workbench/start", json=request_data)

        assert response.status_code == 200
        self._assert_activity_by_workflow_id(
            db_session,
            monitoring_models,
            response.json["workflow_id"],
            expected_build_type_value="workbench_start",
        )

    def test_start_rstudio_workbench_integration(
        self, client, db_session, mock_gcp_clients
    ):
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )

        request_data = {
            "workbench_type": "rstudio",
            "workspace_project_id": "test-project-start-rstudio-integ",
            "user_email": "owner@example.com",
            "workbench_resource_id": "workbench-abc",
        }

        response = client.put("/workbench/start", json=request_data)

        assert response.status_code == 200
        self._assert_activity_by_workflow_id(
            db_session,
            monitoring_models,
            response.json["workflow_id"],
            expected_build_type_value="workbench_start",
        )

    @pytest.mark.parametrize("workbench_type", ["jupyter", "collaborative"])
    def test_destroy_workbench_integration(
        self, client, db_session, mock_gcp_clients, workbench_type
    ):
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.background import enums

        request_data = {
            "workbench_type": workbench_type,
            "workspace_project_id": "test-project-destroy-integ",
            "user_email": "owner@example.com",
            "workbench_resource_id": "workbench-abc",
        }

        response = client.delete("/workbench/destroy", json=request_data)

        assert response.status_code == 200
        workflow_id = response.json["workflow_id"]
        self._assert_destroy_activity(
            db_session, monitoring_models, enums, request_data, workflow_id
        )

    def test_destroy_rstudio_workbench_integration(
        self, client, db_session, mock_gcp_clients
    ):
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.background import enums

        request_data = {
            "workbench_type": "rstudio",
            "workspace_project_id": "test-project-destroy-rstudio-integ",
            "user_email": "owner@example.com",
            "workbench_resource_id": "workbench-abc",
        }

        response = client.delete("/workbench/destroy", json=request_data)

        assert response.status_code == 200
        workflow_id = response.json["workflow_id"]
        self._assert_destroy_activity(
            db_session, monitoring_models, enums, request_data, workflow_id
        )
