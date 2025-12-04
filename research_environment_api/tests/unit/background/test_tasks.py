from unittest.mock import MagicMock

from google.cloud.devtools.cloudbuild_v1 import Build

from research_environment_api.background import tasks, enums
from research_environment_api.modules.monitoring_management import models


class TestTasks:
    def test_process_cloud_build_result_success(
        self, mocker, mock_config, mock_db_session
    ):
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
            workbench_activity_id="act-1",
        )

        # Assert
        assert result == operation

    def test_process_cloud_build_result_failure_no_retry(
        self, mocker, mock_config, mock_db_session
    ):
        """If build fails with non-recoverable error, mark activity as failed."""
        # Arrange
        operation = MagicMock()
        context = (operation, "build-id-123")

        mock_build = MagicMock()
        mock_build.status = Build.Status.FAILURE
        mock_build.steps = [MagicMock(exit_code=1)]

        mock_config.google_cloud_build_client.get_build.return_value = mock_build

        activity = MagicMock(spec=models.WorkbenchActivity)
        mock_db_session.query.return_value.filter_by.return_value.one.return_value = (
            activity
        )

        mock_skip = mocker.patch.object(
            tasks.process_cloud_build_result, "skip_to_last_step", create=True
        )

        # Act
        tasks.process_cloud_build_result(
            operation_context=context,
            user_email="u@t.com",
            workbench_activity_id="act-1",
            fallback_zones=["zone-b"],
        )

        # Assert
        assert (
            "The resource could not be provisioned" in activity.build_error_information
        )
        mock_skip.assert_called_once()

    def test_process_cloud_build_result_retry_logic(
        self, mocker, mock_config, mock_db_session
    ):
        """
        CRITICAL: If build fails with quota error (e.g. code 10), it should retry in next zone.
        """
        # Arrange
        operation = MagicMock()
        context = (operation, "build-id-123")

        mock_build = MagicMock()
        mock_build.status = Build.Status.FAILURE
        mock_build.steps = [MagicMock(exit_code=10)]
        mock_build.substitutions = {
            "_WORKBENCH_TYPE": "jupyter",
            "_PROJECT_ID": "p1",
            "_INSTANCE_NAME": "i1",
        }

        mock_config.google_cloud_build_client.get_build.return_value = mock_build

        mocker.patch.dict(
            "research_environment_api.background.constants.CLOUD_BUILD_ERROR_MESSAGE",
            {10: "Quota Error"},
        )

        mock_create_workflow = mocker.patch(
            "research_environment_api.background.workflows.create_jupyter_workbench"
        )
        mock_create_workflow.return_value = MagicMock()  # Return the chain

        mock_kill = mocker.patch.object(
            tasks.process_cloud_build_result, "kill_chain", create=True
        )

        # Act
        tasks.process_cloud_build_result(
            operation_context=context,
            user_email="u@t.com",
            workbench_activity_id="act-1",
            fallback_zones=["us-central1-b", "us-central1-c"],
        )

        # Assert
        mock_kill.assert_called_once()

        mock_create_workflow.assert_called_once()
        call_kwargs = mock_create_workflow.call_args[1]
        assert call_kwargs["instance_zone"] == "us-central1-b"
        assert call_kwargs["fallback_zones"] == ["us-central1-c"]

    def test_check_and_process_cloud_build_operation_success(
        self, mocker, mock_config, mock_db_session
    ):
        """Test the state machine for finishing a build."""
        # Arrange
        mock_build = MagicMock()
        mock_build.status = Build.Status.SUCCESS
        mock_config.google_cloud_build_client.get_build.return_value = mock_build

        activity = MagicMock(spec=models.WorkbenchActivity)
        activity.build_status = enums.WorkflowStatus.IN_PROGRESS
        mock_db_session.query.return_value.filter_by.return_value.one.return_value = (
            activity
        )

        # Act
        tasks.check_and_process_cloud_build_operation(
            build_id="build-1", workbench_activity_id="act-1"
        )

        # Assert
        assert activity.build_status == enums.WorkflowStatus.SUCCESS
        assert mock_db_session.commit.called
