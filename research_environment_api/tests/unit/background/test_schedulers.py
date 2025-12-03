import pytest
from unittest.mock import MagicMock
from research_environment_api.background import schedulers, enums
from research_environment_api.modules.workbench_management import entities

class TestSchedulers:
    def test_create_jupyter_workbench_scheduler(self, mocker, mock_db_session):
        """Test that scheduler prepares data, saves DB entry, and starts workflow."""
        # Arrange
        # Mock helpers
        mocker.patch("research_environment_api.modules.workbench_management.services.get_available_zones", return_value=["zone-a"])
        mocker.patch("research_environment_api.modules.sharing_management.services.specify_buckets_fusing_permissions", return_value={})
        mocker.patch("research_environment_api.modules.user_group_management.services.get_user_permissions", return_value=[])
        mocker.patch("research_environment_api.background.builds.create_jupyter_workbench_build", return_value=MagicMock())
        mocker.patch("research_environment_api.modules.monitoring_management.services.clear_quotas_cache")

        # Mock Workflow
        mock_workflow_chain = MagicMock()
        mock_create_workflow = mocker.patch(
            "research_environment_api.background.workflows.create_jupyter_workbench",
            return_value=mock_workflow_chain
        )

        request = entities.WorkbenchCreate(
            workspace_project_id="p1", region="us-central1", machine_type="n1",
            disk_size=100, gpu_accelerator_type=None, dataset_identifier="ds1",
            user_email="u@t.com", bucket_name="b1", vm_image="img",
            sharing_bucket_identifiers=[], user_groups=[], collaborative="false"
        )

        # Act
        schedulers.create_jupyter_workbench(request)

        # Assert
        # 1. DB Entry created
        assert mock_db_session.add.called
        args, _ = mock_db_session.add.call_args
        activity = args[0]
        assert activity.build_type == enums.BuildType.WORKBENCH_CREATION
        assert activity.build_status == enums.WorkflowStatus.IN_PROGRESS

        # 2. Workflow called
        mock_create_workflow.assert_called_once()
        mock_workflow_chain.assert_called_once() # The chain () was called