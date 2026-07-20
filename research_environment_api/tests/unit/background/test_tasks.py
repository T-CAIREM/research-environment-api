from unittest.mock import MagicMock

from google.cloud.devtools.cloudbuild_v1 import Build

from research_environment_api.background import tasks, enums
from research_environment_api.modules.monitoring_management import models
from research_environment_api.modules.workbench_management.entities import (
    WorkbenchStatus,
)


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

    def test_mark_stale_workbenches_marks_deleted_project_and_continues(
        self, mocker, mock_config, mock_db_session
    ):
        """
        Regression: a monitoring entry whose workbench/project no longer exists
        must be marked deleted (not raise StopIteration), and a failure on one
        entry must not stop the remaining entries from being processed.
        """

        # Arrange: three still-active monitoring entries.
        def _entry(workbench_id):
            entry = MagicMock(spec=models.WorkbenchMonitoringData)
            entry.workbench_id = workbench_id
            entry.user_email = "u@t.com"
            entry.deleted_at = None
            return entry

        gone, stopped, running = (
            _entry("wb-gone"),
            _entry("wb-stopped"),
            _entry("wb-running"),
        )
        rows = [(gone, "proj-gone"), (stopped, "proj-a"), (running, "proj-a")]
        (
            mock_db_session.query.return_value.join.return_value
        ).filter.return_value.all.return_value = rows

        stopped_workbench = MagicMock()
        stopped_workbench.status = WorkbenchStatus.STOPPED
        running_workbench = MagicMock()
        running_workbench.status = WorkbenchStatus.RUNNING

        # First lookup raises (deleted project), the rest resolve normally.
        mocker.patch.object(
            tasks.workbench_services,
            "get_compute_engine_workbench",
            side_effect=[
                tasks.workbench_services.WorkbenchNotFoundError("gone"),
                stopped_workbench,
                running_workbench,
            ],
        )

        # Act
        tasks.mark_monitoring_entry_for_stale_workbenches()

        # Assert: the gone project and the stopped workbench are marked deleted;
        # the running one is left active; the batch was not aborted early.
        assert gone.deleted_at is not None
        assert stopped.deleted_at is not None
        assert running.deleted_at is None
        assert mock_db_session.commit.called

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
