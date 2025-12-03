import pytest
from unittest.mock import MagicMock
from research_environment_api.background import operations, enums


class TestOperations:
    def test_build_operation_status_success(self, mock_config):
        """Test BuildOperation maps successful google op to SUCCESS."""
        # Arrange
        mock_google_op = MagicMock()
        mock_google_op.done = True
        mock_google_op.error.code = 0  # No error

        mock_config.google_operations_client.get_operation.return_value = mock_google_op

        op = operations.BuildOperation("op-123")

        # Act
        status = op.status()

        # Assert
        assert status == enums.OperationStatus.SUCCESS

    def test_build_operation_status_failure(self, mock_config):
        """Test BuildOperation maps error google op to FAILURE."""
        # Arrange
        mock_google_op = MagicMock()
        mock_google_op.done = True
        mock_google_op.error.code = 1  # Error present

        mock_config.google_operations_client.get_operation.return_value = mock_google_op

        op = operations.BuildOperation("op-123")

        # Act
        status = op.status()

        # Assert
        assert status == enums.OperationStatus.FAILURE