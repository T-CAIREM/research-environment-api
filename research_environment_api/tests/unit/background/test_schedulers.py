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
        mocker.patch(
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
