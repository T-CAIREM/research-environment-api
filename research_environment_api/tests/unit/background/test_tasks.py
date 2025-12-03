import pytest
from unittest.mock import MagicMock, patch
from google.cloud.devtools.cloudbuild_v1 import Build
from research_environment_api.background import tasks, enums
from research_environment_api.modules.monitoring_management import models


class TestTasks:
    """Test Celery tasks logic."""

    def test_process_cloud_build_result_success(self, mocker, mock_config, mock_db_session):
        """If build succeeds, do nothing (pass through)."""
        # Arrange
        operation = MagicMock()
        context = (operation, "build-id-123")

        mock_build = MagicMock()
        mock_build.status = Build.Status.SUCCESS
        mock_config.google_cloud_build_client.get_build.return_value = mock_build

        # Act
        result = tasks.process_cloud_build_result(
            operation_context=context,
            user_email="u@t.com",
            workbench_activity_id="act-1"
        )

        # Assert
        assert result == operation  # Passed through
        # DB should generally not be modified here on success (handled by check_and_process)

    def test_process_cloud_build_result_failure_no_retry(self, mocker, mock_config, mock_db_session):
        """If build fails with non-recoverable error, mark activity as failed."""
        # Arrange
        operation = MagicMock()
        context = (operation, "build-id-123")

        mock_build = MagicMock()
        mock_build.status = Build.Status.FAILURE
        # Exit code 1 usually means Terraform error (logic), not Google flake
        mock_build.steps = [MagicMock(exit_code=1)]

        mock_config.google_cloud_build_client.get_build.return_value = mock_build

        # Database Setup
        activity = MagicMock(spec=models.WorkbenchActivity)
        mock_db_session.query.return_value.filter_by.return_value.one.return_value = activity

        # Mock Celery task methods
        mock_self = MagicMock()

        # Act
        # call the function directly, bypassing celery decorator wrapper behavior for unit testing
        # We assume 'process_cloud_build_result' is the function inside the task
        # Since it's bound, we pass 'mock_self' as first arg
        tasks.process_cloud_build_result.__wrapped__(
            mock_self,
            context,
            "u@t.com",
            "act-1",
            fallback_zones=["zone-b"]  # Even with fallback zones...
        )

        # Assert
        # ...it should fail because code 1 is likely not in CONSTANTS.RECOVERABLE
        assert "The resource could not be provisioned" in activity.build_error_information
        mock_self.skip_to_last_step.assert_called_once()

    def test_process_cloud_build_result_retry_logic(self, mocker, mock_config, mock_db_session):
        """
        CRITICAL: If build fails with quota error (e.g. code 10), it should retry in next zone.
        """
        # Arrange
        operation = MagicMock()
        context = (operation, "build-id-123")

        mock_build = MagicMock()
        mock_build.status = Build.Status.FAILURE
        # Let's say code 10 is mapped to a Quota Error in constants (Mocking this)
        mock_build.steps = [MagicMock(exit_code=10)]
        mock_build.substitutions = {
            "_WORKBENCH_TYPE": "jupyter",
            "_PROJECT_ID": "p1",
            "_INSTANCE_NAME": "i1"
        }

        mock_config.google_cloud_build_client.get_build.return_value = mock_build

        # Mock Constants to ensure code 10 is recoverable
        mocker.patch.dict("research_environment_api.background.constants.CLOUD_BUILD_ERROR_MESSAGE",
                          {10: "Quota Error"})

        # Mock the workflow trigger
        mock_create_workflow = mocker.patch("research_environment_api.background.workflows.create_jupyter_workbench")
        mock_create_workflow.return_value = MagicMock()  # Return the chain

        mock_self = MagicMock()

        # Act
        tasks.process_cloud_build_result.__wrapped__(
            mock_self,
            context,
            "u@t.com",
            "act-1",
            fallback_zones=["us-central1-b", "us-central1-c"]  # List of zones
        )

        # Assert
        # 1. Should NOT set error info (because it's retrying)
        # 2. Should kill current chain
        mock_self.kill_chain.assert_called_once()

        # 3. Should trigger new workflow with NEXT zone
        mock_create_workflow.assert_called_once()
        call_kwargs = mock_create_workflow.call_args[1]
        assert call_kwargs['instance_zone'] == "us-central1-b"  # The first fallback
        assert call_kwargs['fallback_zones'] == ["us-central1-c"]  # The remaining fallbacks

    def test_check_and_process_cloud_build_operation_success(self, mocker, mock_config, mock_db_session):
        """Test the state machine for finishing a build."""
        # Arrange
        mock_build = MagicMock()
        mock_build.status = Build.Status.SUCCESS
        mock_config.google_cloud_build_client.get_build.return_value = mock_build

        activity = MagicMock(spec=models.WorkbenchActivity)
        activity.build_status = enums.WorkflowStatus.IN_PROGRESS
        mock_db_session.query.return_value.filter_by.return_value.one.return_value = activity

        mock_self = MagicMock()

        # Act
        tasks.check_and_process_cloud_build_operation.__wrapped__(
            mock_self, "build-1", "act-1"
        )

        # Assert
        assert activity.build_status == enums.WorkflowStatus.SUCCESS
        assert mock_db_session.commit.called