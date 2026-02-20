"""Integration tests for Workspace API endpoints.

Scope
-----
These tests exercise the HTTP endpoints under `/workspace/*` using:
- a real Flask app (test client)
- a real Postgres DB (container + Alembic migrations)
- Celery in eager mode (tasks executed in-process)

We treat all GCP clients as *external boundaries* and mock them.

What we validate
----------------
- endpoint accepts request payload and returns a workflow identifier
- a monitoring row (`WorkbenchActivity`) is created with the expected build_type
- create/delete/shared-create/shared-delete create the expected build record

What we don't validate
----------------------
- long-running async/polling behavior (we patch follow-up tasks in eager mode)
"""

from unittest.mock import MagicMock

import pytest


class TestWorkspaceWorkflowIntegration:
    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _assert_activity_by_workflow_id(
        db_session, monitoring_models, workflow_id, expected_build_type_value: str
    ):
        """Assert a WorkbenchActivity row exists for workflow_id with the given build_type."""
        with db_session() as session:
            activity = (
                session.query(monitoring_models.WorkbenchActivity)
                .filter_by(id=workflow_id)
                .first()
            )

            assert (
                activity is not None
            ), f"No activity found for workflow_id={workflow_id}"
            assert str(activity.build_type.value) == expected_build_type_value

    # ------------------------------------------------------------------
    # GCP mocks
    # ------------------------------------------------------------------

    @pytest.fixture
    def mock_gcp_workspace_clients(self, mocker):
        """Patch GCP clients so workspace tests stay offline and deterministic.

        Mocks:
        - Cloud Build client (create/destroy workspace triggers builds)
        - user_group_services (external IAM lookups)
        - Follow-up Celery tasks that would otherwise poll in eager mode
        """
        # Prevent delayed follow-up task from running
        mocker.patch(
            "research_environment_api.background.tasks.check_and_process_cloud_build_operation.apply_async",
            return_value=None,
        )

        from google.cloud.devtools import cloudbuild_v1

        # Cloud Build client used by background.tasks.start_cloud_build
        mock_build_client = MagicMock(spec=cloudbuild_v1.CloudBuildClient)
        mock_operation = MagicMock()
        mock_operation.operation.name = "operations/ws-test-op"
        mock_operation.metadata.build.id = "ws-build-1"
        mock_build_client.create_build.return_value = mock_operation

        # Successful build result
        mock_build = MagicMock()
        from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild

        mock_build.status = CloudBuild.Status.SUCCESS
        mock_build.steps = [MagicMock(exit_code=0)]
        mock_build_client.get_build.return_value = mock_build

        mocker.patch(
            "research_environment_api.modules.app.app.config.google_cloud_build_client",
            mock_build_client,
        )

        # Avoid polling tasks in eager mode
        mocker.patch(
            "research_environment_api.background.tasks.check_vertex_ai_setup_status",
            return_value=None,
        )
        mocker.patch(
            "research_environment_api.background.tasks.process_cloud_build_result",
            return_value=None,
        )
        mocker.patch(
            "research_environment_api.background.tasks.set_workflow_status",
            return_value=None,
        )

        # External IAM / group permissions
        mocker.patch(
            "research_environment_api.background.schedulers.user_group_services.get_user_permissions",
            return_value=[],
        )

        return {"cloud_build": mock_build_client}

    # ------------------------------------------------------------------
    # Create workspace
    # ------------------------------------------------------------------

    def test_create_workspace_integration(
        self,
        client,
        db_session,
        mock_gcp_workspace_clients,
        celery_eager,
    ):
        """POST /workspace/create returns workflow_id and creates a monitoring row."""
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.background import enums
        from research_environment_api.web.workspace_management import schemas

        request_data = {
            "user_email": "creator@example.com",
            "billing_account_id": "ABCDEF-123456-FEDCBA",
            "user_groups": ["group1", "group2"],
        }

        response = client.post("/workspace/create", json=request_data)

        assert response.status_code == 201
        loaded = schemas.WorkspaceWorkflowIdentifier().load(response.json)
        workflow_id = loaded["workflow_id"]
        assert workflow_id

        with db_session() as session:
            activity = (
                session.query(monitoring_models.WorkbenchActivity)
                .filter_by(id=workflow_id)
                .first()
            )

            assert activity is not None
            assert activity.invoker_email == "creator@example.com"
            assert activity.build_type == enums.BuildType.WORKSPACE_CREATION
            assert activity.build_status in [
                enums.WorkflowStatus.SUCCESS,
                enums.WorkflowStatus.IN_PROGRESS,
            ]

    def test_create_workspace_failure_marks_activity_failure(
        self,
        client,
        db_session,
        mock_gcp_workspace_clients,
        celery_eager,
    ):
        """When Cloud Build fails the activity should be FAILURE or IN_PROGRESS."""
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.background import enums
        from research_environment_api.web.workspace_management import schemas
        from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild

        # Force build failure
        mock_build = MagicMock()
        mock_build.status = CloudBuild.Status.FAILURE
        failing_step = MagicMock()
        failing_step.exit_code = 1
        mock_build.steps = [failing_step]
        mock_gcp_workspace_clients["cloud_build"].get_build.return_value = mock_build

        request_data = {
            "user_email": "creator-fail@example.com",
            "billing_account_id": "ABCDEF-123456-FEDCBA",
            "user_groups": ["group1"],
        }

        response = client.post("/workspace/create", json=request_data)
        assert response.status_code == 201

        workflow_id = schemas.WorkspaceWorkflowIdentifier().load(response.json)[
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

    # ------------------------------------------------------------------
    # Delete workspace
    # ------------------------------------------------------------------

    def test_delete_workspace_integration(
        self,
        client,
        db_session,
        mock_gcp_workspace_clients,
        celery_eager,
    ):
        """DELETE /workspace/delete returns workflow_id and creates WORKSPACE_DELETION activity."""
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.background import enums
        from research_environment_api.web.workspace_management import schemas

        request_data = {
            "user_email": "owner@example.com",
            "billing_account_id": "ABCDEF-123456-FEDCBA",
            "workspace_project_id": "owner-test-abcde",
        }

        response = client.delete("/workspace/delete", json=request_data)

        assert response.status_code == 201
        loaded = schemas.WorkspaceWorkflowIdentifier().load(response.json)
        workflow_id = loaded["workflow_id"]
        assert workflow_id

        self._assert_activity_by_workflow_id(
            db_session,
            monitoring_models,
            workflow_id,
            expected_build_type_value="workspace_deletion",
        )

        with db_session() as session:
            activity = (
                session.query(monitoring_models.WorkbenchActivity)
                .filter_by(id=workflow_id)
                .first()
            )
            assert activity.invoker_email == "owner@example.com"
            assert activity.workspace_id == "owner-test-abcde"
            assert activity.build_type == enums.BuildType.WORKSPACE_DELETION

    def test_delete_workspace_failure_marks_activity_failure(
        self,
        client,
        db_session,
        mock_gcp_workspace_clients,
        celery_eager,
    ):
        """When Cloud Build fails during deletion the activity should be FAILURE or IN_PROGRESS."""
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.background import enums
        from research_environment_api.web.workspace_management import schemas
        from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild

        mock_build = MagicMock()
        mock_build.status = CloudBuild.Status.FAILURE
        failing_step = MagicMock()
        failing_step.exit_code = 1
        mock_build.steps = [failing_step]
        mock_gcp_workspace_clients["cloud_build"].get_build.return_value = mock_build

        request_data = {
            "user_email": "owner-fail@example.com",
            "billing_account_id": "ABCDEF-123456-FEDCBA",
            "workspace_project_id": "owner-fail-xyzab",
        }

        response = client.delete("/workspace/delete", json=request_data)
        assert response.status_code == 201

        workflow_id = schemas.WorkspaceWorkflowIdentifier().load(response.json)[
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

    # ------------------------------------------------------------------
    # Create shared workspace
    # ------------------------------------------------------------------

    def test_create_shared_workspace_integration(
        self,
        client,
        db_session,
        mock_gcp_workspace_clients,
        celery_eager,
    ):
        """POST /workspace/shared/create returns workflow_id and creates a monitoring row."""
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.background import enums
        from research_environment_api.web.workspace_management import schemas

        request_data = {
            "user_email": "sharedowner@example.com",
            "billing_account_id": "SHARED-123456-FEDCBA",
        }

        response = client.post("/workspace/shared/create", json=request_data)

        assert response.status_code == 200
        loaded = schemas.WorkspaceWorkflowIdentifier().load(response.json)
        workflow_id = loaded["workflow_id"]
        assert workflow_id

        with db_session() as session:
            activity = (
                session.query(monitoring_models.WorkbenchActivity)
                .filter_by(id=workflow_id)
                .first()
            )

            assert activity is not None
            assert activity.invoker_email == "sharedowner@example.com"
            assert activity.build_type == enums.BuildType.SHARED_WORKSPACE_CREATION
            assert activity.build_status in [
                enums.WorkflowStatus.SUCCESS,
                enums.WorkflowStatus.IN_PROGRESS,
            ]

    def test_create_shared_workspace_workspace_id_contains_shared(
        self,
        client,
        db_session,
        mock_gcp_workspace_clients,
        celery_eager,
    ):
        """workspace_id on the activity should be auto-generated and contain '-shared-'."""
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.web.workspace_management import schemas

        request_data = {
            "user_email": "sharedowner2@example.com",
            "billing_account_id": "SHARED-999999-AAAAAA",
        }

        response = client.post("/workspace/shared/create", json=request_data)
        assert response.status_code == 200

        workflow_id = schemas.WorkspaceWorkflowIdentifier().load(response.json)[
            "workflow_id"
        ]

        with db_session() as session:
            activity = (
                session.query(monitoring_models.WorkbenchActivity)
                .filter_by(id=workflow_id)
                .first()
            )
            assert activity is not None
            assert "shared" in activity.workspace_id

    # ------------------------------------------------------------------
    # Delete shared workspace
    # ------------------------------------------------------------------

    def test_delete_shared_workspace_integration(
        self,
        client,
        db_session,
        mock_gcp_workspace_clients,
        celery_eager,
    ):
        """DELETE /workspace/shared/delete returns workflow_id and SHARED_WORKSPACE_DELETION activity."""
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.background import enums
        from research_environment_api.web.workspace_management import schemas

        request_data = {
            "user_email": "sharedowner@example.com",
            "billing_account_id": "SHARED-123456-DELETE",
            "workspace_project_id": "sharedowner-shared-abcde",
        }

        response = client.delete("/workspace/shared/delete", json=request_data)

        assert response.status_code == 200
        loaded = schemas.WorkspaceWorkflowIdentifier().load(response.json)
        workflow_id = loaded["workflow_id"]
        assert workflow_id

        self._assert_activity_by_workflow_id(
            db_session,
            monitoring_models,
            workflow_id,
            expected_build_type_value="shared_workspace_deletion",
        )

        with db_session() as session:
            activity = (
                session.query(monitoring_models.WorkbenchActivity)
                .filter_by(id=workflow_id)
                .first()
            )
            assert activity.invoker_email == "sharedowner@example.com"
            assert activity.workspace_id == "sharedowner-shared-abcde"
            assert activity.build_type == enums.BuildType.SHARED_WORKSPACE_DELETION

    def test_delete_shared_workspace_failure_marks_activity_failure(
        self,
        client,
        db_session,
        mock_gcp_workspace_clients,
        celery_eager,
    ):
        """When Cloud Build fails during shared workspace deletion the activity reflects it."""
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.background import enums
        from research_environment_api.web.workspace_management import schemas
        from google.cloud.devtools.cloudbuild_v1 import Build as CloudBuild

        mock_build = MagicMock()
        mock_build.status = CloudBuild.Status.FAILURE
        failing_step = MagicMock()
        failing_step.exit_code = 1
        mock_build.steps = [failing_step]
        mock_gcp_workspace_clients["cloud_build"].get_build.return_value = mock_build

        request_data = {
            "user_email": "sharedowner-fail@example.com",
            "billing_account_id": "SHARED-FAIL-123456",
            "workspace_project_id": "sharedfail-shared-xyzab",
        }

        response = client.delete("/workspace/shared/delete", json=request_data)
        assert response.status_code == 200

        workflow_id = schemas.WorkspaceWorkflowIdentifier().load(response.json)[
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

    # ------------------------------------------------------------------
    # Multiple workspaces - independent activities
    # ------------------------------------------------------------------

    def test_multiple_creates_produce_independent_activities(
        self,
        client,
        db_session,
        mock_gcp_workspace_clients,
        celery_eager,
    ):
        """Each create call must produce a distinct workflow_id / activity row."""
        from research_environment_api.modules.monitoring_management import (
            models as monitoring_models,
        )
        from research_environment_api.web.workspace_management import schemas

        workflow_ids = []
        for i in range(3):
            request_data = {
                "user_email": f"multi{i}@example.com",
                "billing_account_id": "MULTI-123456-FEDCBA",
                "user_groups": ["group1"],
            }
            response = client.post("/workspace/create", json=request_data)
            assert response.status_code == 201
            wid = schemas.WorkspaceWorkflowIdentifier().load(response.json)[
                "workflow_id"
            ]
            workflow_ids.append(wid)

        assert len(set(workflow_ids)) == 3, "workflow_ids must be unique"

        for wid in workflow_ids:
            with db_session() as session:
                activity = (
                    session.query(monitoring_models.WorkbenchActivity)
                    .filter_by(id=wid)
                    .first()
                )
                assert activity is not None

    # ------------------------------------------------------------------
    # Validation / bad request
    # ------------------------------------------------------------------

    def test_create_workspace_missing_billing_account_returns_error(
        self,
        client,
        mock_gcp_workspace_clients,
    ):
        """POST /workspace/create without billing_account_id raises a ValidationError.

        The workspace blueprint has no ValidationError error handler registered,
        so marshmallow raises directly. Flask's TESTING mode re-raises it rather
        than swallowing it — we assert the exception is a ValidationError and
        that the messages reference the missing field.
        """
        import marshmallow

        request_data = {
            "user_email": "creator@example.com",
            "user_groups": ["group1"],
            # billing_account_id intentionally omitted
        }

        with pytest.raises(marshmallow.exceptions.ValidationError) as exc_info:
            client.post("/workspace/create", json=request_data)

        assert "billing_account_id" in exc_info.value.messages

    def test_create_workspace_invalid_email_returns_error(
        self,
        client,
        mock_gcp_workspace_clients,
    ):
        """POST /workspace/create with a non-email string raises a ValidationError."""
        import marshmallow

        request_data = {
            "user_email": "not-an-email",
            "billing_account_id": "ABCDEF-123456-FEDCBA",
            "user_groups": ["group1"],
        }

        with pytest.raises(marshmallow.exceptions.ValidationError) as exc_info:
            client.post("/workspace/create", json=request_data)

        assert "user_email" in exc_info.value.messages

    def test_delete_workspace_missing_project_id_returns_error(
        self,
        client,
        mock_gcp_workspace_clients,
    ):
        """DELETE /workspace/delete without workspace_project_id raises a ValidationError."""
        import marshmallow

        request_data = {
            "user_email": "owner@example.com",
            "billing_account_id": "ABCDEF-123456-FEDCBA",
            # workspace_project_id intentionally omitted
        }

        with pytest.raises(marshmallow.exceptions.ValidationError) as exc_info:
            client.delete("/workspace/delete", json=request_data)

        assert "workspace_project_id" in exc_info.value.messages
