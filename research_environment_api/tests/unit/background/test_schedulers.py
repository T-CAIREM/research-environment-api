from unittest.mock import MagicMock

from research_environment_api.background import schedulers, enums
from research_environment_api.modules.workbench_management import entities


class TestSchedulers:
    def test_create_jupyter_workbench_scheduler(self, mocker, mock_db_session):
        """Test that scheduler prepares data, saves DB entry, and starts workflow."""
        # Arrange
        mocker.patch(
            "research_environment_api.modules.workbench_management.services.get_available_zones",
            return_value=["zone-a"],
        )
        mocker.patch(
            "research_environment_api.modules.sharing_management.services.specify_buckets_fusing_permissions",
            return_value={},
        )
        mocker.patch(
            "research_environment_api.modules.user_group_management.services.get_user_permissions",
            return_value=[],
        )
        mock_create_build = mocker.patch(
            "research_environment_api.background.builds.create_jupyter_workbench_build",
            return_value=MagicMock(),
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.clear_quotas_cache"
        )

        mock_workflow_chain = MagicMock()
        mock_create_workflow = mocker.patch(
            "research_environment_api.background.workflows.create_jupyter_workbench",
            return_value=mock_workflow_chain,
        )

        request = entities.WorkbenchCreate(
            workbench_type="jupyter",
            workspace_project_id="p1",
            region="us-central1",
            machine_type="n1",
            disk_size=100,
            gpu_accelerator_type=None,
            dataset_identifier="ds1",
            user_email="u@t.com",
            bucket_name="b1",
            sharing_bucket_identifiers=[],
            user_groups=[],
            workspace_numeric_id="123",
            memory=16.0,
            cpu=4,
        )

        # Act
        schedulers.create_jupyter_workbench(request)

        # Assert
        assert mock_db_session.add.called
        args, _ = mock_db_session.add.call_args
        activity = args[0]
        assert activity.build_type == enums.BuildType.WORKBENCH_CREATION
        mock_create_workflow.assert_called_once()
        mock_workflow_chain.assert_called_once()

        # The mount mode and the VM image family reach the build unchanged.
        build_kwargs = mock_create_build.call_args.kwargs
        assert build_kwargs["object_prefix"] == ""
        assert build_kwargs["writable"] is False
        assert build_kwargs["vm_image_family"] == "workbench-instances"

    def test_create_jupyter_workbench_scheduler_writable_draft(
        self, mocker, mock_db_session
    ):
        """A writable draft request threads its mount settings to the build."""
        # Arrange
        mocker.patch(
            "research_environment_api.modules.workbench_management.services.get_available_zones",
            return_value=["zone-a"],
        )
        mocker.patch(
            "research_environment_api.modules.sharing_management.services.specify_buckets_fusing_permissions",
            return_value={},
        )
        mocker.patch(
            "research_environment_api.modules.user_group_management.services.get_user_permissions",
            return_value=[],
        )
        mock_create_build = mocker.patch(
            "research_environment_api.background.builds.create_jupyter_workbench_build",
            return_value=MagicMock(),
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.clear_quotas_cache"
        )
        mocker.patch(
            "research_environment_api.background.workflows.create_jupyter_workbench",
            return_value=MagicMock(),
        )

        request = entities.WorkbenchCreate(
            workbench_type="jupyter",
            workspace_project_id="p1",
            region="us-central1",
            machine_type="n1",
            disk_size=100,
            gpu_accelerator_type=None,
            dataset_identifier="ds1",
            user_email="u@t.com",
            bucket_name="b1",
            sharing_bucket_identifiers=[],
            user_groups=[],
            workspace_numeric_id="123",
            memory=16.0,
            cpu=4,
            object_prefix="active-projects/my-draft",
            writable=True,
        )

        # Act
        schedulers.create_jupyter_workbench(request)

        # Assert
        build_kwargs = mock_create_build.call_args.kwargs
        assert build_kwargs["object_prefix"] == "active-projects/my-draft"
        assert build_kwargs["writable"] is True
        assert build_kwargs["vm_image_family"] == "workbench-instances"

    def test_destroy_jupyter_workbench_scheduler_replays_mount_settings(
        self, mocker, mock_db_session
    ):
        """Destroy rebuilds terraform inputs from the instance's metadata.

        RE-API stores no per-workbench record, so the prefix and mode have to
        come back off the `Workbench` entity read from GCE.
        """
        # Arrange
        mock_destroy_build = mocker.patch(
            "research_environment_api.background.builds.destroy_jupyter_workbench_build",
            return_value=MagicMock(),
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.clear_quotas_cache"
        )
        mocker.patch(
            "research_environment_api.background.workflows.destroy_jupyter_workbench",
            return_value=MagicMock(),
        )

        workbench = MagicMock(
            id="wb-id",
            zone="us-central1-a",
            region="us-central1",
            object_prefix="active-projects/my-draft",
            writable=True,
        )
        request = entities.WorkbenchDestroy(
            workspace_project_id="p1",
            workbench_resource_id="wb-id",
            user_email="u@t.com",
            workbench_type="jupyter",
        )

        # Act
        schedulers.destroy_jupyter_workbench_flow(request, workbench)

        # Assert
        build_kwargs = mock_destroy_build.call_args.kwargs
        assert build_kwargs["object_prefix"] == "active-projects/my-draft"
        assert build_kwargs["writable"] is True

    def test_stop_compute_engine_workbench_scheduler(self, mocker, mock_db_session):
        """Test stopping a workbench scheduler."""
        # Arrange
        mock_wb = MagicMock(id="wb-id", zone="us-central1-a", region="us-central1")
        mocker.patch(
            "research_environment_api.modules.workbench_management.services.get_compute_engine_workbench",
            return_value=mock_wb,
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.clear_quotas_cache"
        )

        mock_workflow_chain = MagicMock()
        mock_stop_workflow = mocker.patch(
            "research_environment_api.background.workflows.stop_compute_engine_workbench",
            return_value=mock_workflow_chain,
        )

        request = entities.WorkbenchToggleState(
            workspace_project_id="p1",
            workbench_resource_id="wb-id",
            user_email="u@t.com",
            workbench_type="jupyter",
        )

        # Act
        schedulers.stop_compute_engine_workbench(request)

        # Assert
        assert mock_db_session.add.called
        args, _ = mock_db_session.add.call_args
        activity = args[0]
        assert activity.build_type == enums.BuildType.WORKBENCH_STOP
        mock_stop_workflow.assert_called_once()
        mock_workflow_chain.assert_called_once()

    def test_create_rstudio_workbench_scheduler_writable_draft(
        self, mocker, mock_db_session
    ):
        """A writable draft request threads its mount settings to the build."""
        # Arrange
        mocker.patch(
            "research_environment_api.modules.workbench_management.services.get_available_zones",
            return_value=["zone-a"],
        )
        mocker.patch(
            "research_environment_api.modules.sharing_management.services.specify_buckets_fusing_permissions",
            return_value={},
        )
        mocker.patch(
            "research_environment_api.modules.user_group_management.services.get_user_permissions",
            return_value=[],
        )
        mock_create_build = mocker.patch(
            "research_environment_api.background.builds.create_rstudio_workbench_build",
            return_value=MagicMock(),
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.clear_quotas_cache"
        )
        mocker.patch(
            "research_environment_api.background.workflows.create_rstudio_workbench",
            return_value=MagicMock(),
        )

        request = entities.WorkbenchCreate(
            workbench_type="rstudio",
            workspace_project_id="p1",
            region="us-central1",
            machine_type="n1",
            disk_size=100,
            gpu_accelerator_type=None,
            dataset_identifier="ds1",
            user_email="u@t.com",
            bucket_name="b1",
            sharing_bucket_identifiers=[],
            user_groups=[],
            workspace_numeric_id="123",
            memory=16.0,
            cpu=4,
            object_prefix="active-projects/my-draft",
            writable=True,
        )

        # Act
        schedulers.create_rstudio_workbench(request)

        # Assert
        build_kwargs = mock_create_build.call_args.kwargs
        assert build_kwargs["object_prefix"] == "active-projects/my-draft"
        assert build_kwargs["writable"] is True

    def test_create_rstudio_workbench_scheduler_defaults(self, mocker, mock_db_session):
        """A published request keeps today's whole-bucket, read-only mount."""
        # Arrange
        mocker.patch(
            "research_environment_api.modules.workbench_management.services.get_available_zones",
            return_value=["zone-a"],
        )
        mocker.patch(
            "research_environment_api.modules.sharing_management.services.specify_buckets_fusing_permissions",
            return_value={},
        )
        mocker.patch(
            "research_environment_api.modules.user_group_management.services.get_user_permissions",
            return_value=[],
        )
        mock_create_build = mocker.patch(
            "research_environment_api.background.builds.create_rstudio_workbench_build",
            return_value=MagicMock(),
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.clear_quotas_cache"
        )
        mocker.patch(
            "research_environment_api.background.workflows.create_rstudio_workbench",
            return_value=MagicMock(),
        )

        request = entities.WorkbenchCreate(
            workbench_type="rstudio",
            workspace_project_id="p1",
            region="us-central1",
            machine_type="n1",
            disk_size=100,
            gpu_accelerator_type=None,
            dataset_identifier="ds1",
            user_email="u@t.com",
            bucket_name="b1",
            sharing_bucket_identifiers=[],
            user_groups=[],
            workspace_numeric_id="123",
            memory=16.0,
            cpu=4,
        )

        # Act
        schedulers.create_rstudio_workbench(request)

        # Assert
        build_kwargs = mock_create_build.call_args.kwargs
        assert build_kwargs["object_prefix"] == ""
        assert build_kwargs["writable"] is False

    def test_update_rstudio_workbench_scheduler_replays_mount_settings(
        self, mocker, mock_db_session
    ):
        """The RStudio update re-applies terraform, so it must replay the mount.

        The settings come off the `Workbench` entity read back from the
        instance's metadata; dropping them would rebind IAM to the whole bucket.
        """
        # Arrange
        workbench = MagicMock(
            id="wb-id",
            zone="us-central1-a",
            region="us-central1",
            object_prefix="active-projects/my-draft",
            writable=True,
        )
        mocker.patch(
            "research_environment_api.modules.workbench_management.services.get_compute_engine_workbench",
            return_value=workbench,
        )
        mocker.patch(
            "research_environment_api.modules.sharing_management.services.specify_buckets_fusing_permissions",
            return_value={},
        )
        mocker.patch(
            "research_environment_api.modules.user_group_management.services.get_roles_associated_with_service_account",
            return_value=[],
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.clear_quotas_cache"
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.check_workbench_update_quotas"
        )
        mock_update_build = mocker.patch(
            "research_environment_api.background.builds.update_rstudio_workbench_build",
            return_value=MagicMock(),
        )
        mocker.patch(
            "research_environment_api.background.workflows.update_rstudio_workbench",
            return_value=MagicMock(),
        )

        request = entities.WorkbenchUpdate(
            workspace_project_id="p1",
            workbench_resource_id="wb-id",
            user_email="u@t.com",
            workbench_type="rstudio",
            machine_type="n1",
        )

        # Act
        schedulers.update_rstudio_workbench(request)

        # Assert
        build_kwargs = mock_update_build.call_args.kwargs
        assert build_kwargs["object_prefix"] == "active-projects/my-draft"
        assert build_kwargs["writable"] is True

    def test_renew_rstudio_ssl_certificate_replays_mount_settings(
        self, mocker, mock_db_session
    ):
        """Certificate renewal runs the same apply, so it replays the mount too."""
        # Arrange
        workbench = MagicMock(
            id="wb-id",
            zone="us-central1-a",
            region="us-central1",
            object_prefix="active-projects/my-draft",
            writable=True,
        )
        mocker.patch(
            "research_environment_api.modules.workbench_management.services.get_compute_engine_workbench",
            return_value=workbench,
        )
        mocker.patch(
            "research_environment_api.modules.sharing_management.services.specify_buckets_fusing_permissions",
            return_value={},
        )
        mocker.patch(
            "research_environment_api.modules.user_group_management.services.get_roles_associated_with_service_account",
            return_value=[],
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.clear_quotas_cache"
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.check_workbench_update_quotas"
        )
        mock_update_build = mocker.patch(
            "research_environment_api.background.builds.update_rstudio_workbench_build",
            return_value=MagicMock(),
        )
        mocker.patch(
            "research_environment_api.background.workflows.update_rstudio_workbench",
            return_value=MagicMock(),
        )

        request = entities.WorkbenchRenewSSLCertificate(
            workspace_project_id="p1",
            workbench_resource_id="wb-id",
            user_email="u@t.com",
            workbench_type="rstudio",
        )

        # Act
        schedulers.renew_rstudio_ssl_certificate(request)

        # Assert
        build_kwargs = mock_update_build.call_args.kwargs
        assert build_kwargs["object_prefix"] == "active-projects/my-draft"
        assert build_kwargs["writable"] is True

    def test_destroy_rstudio_workbench_scheduler_replays_mount_settings(
        self, mocker, mock_db_session
    ):
        """Destroy rebuilds terraform inputs from the instance's metadata."""
        # Arrange
        mock_destroy_build = mocker.patch(
            "research_environment_api.background.builds.destroy_rstudio_workbench_build",
            return_value=MagicMock(),
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.clear_quotas_cache"
        )
        mocker.patch(
            "research_environment_api.background.workflows.destroy_rstudio_workbench",
            return_value=MagicMock(),
        )

        workbench = MagicMock(
            id="wb-id",
            zone="us-central1-a",
            region="us-central1",
            object_prefix="active-projects/my-draft",
            writable=True,
        )
        request = entities.WorkbenchDestroy(
            workspace_project_id="p1",
            workbench_resource_id="wb-id",
            user_email="u@t.com",
            workbench_type="rstudio",
        )

        # Act
        schedulers.destroy_rstudio_workbench_flow(request, workbench)

        # Assert
        build_kwargs = mock_destroy_build.call_args.kwargs
        assert build_kwargs["object_prefix"] == "active-projects/my-draft"
        assert build_kwargs["writable"] is True
