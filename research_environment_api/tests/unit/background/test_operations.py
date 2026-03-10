from unittest.mock import MagicMock

from research_environment_api.background import operations, enums


class TestOperations:
    def test_build_operation_status_success(self, mock_config):
        """Test BuildOperation maps successful google op to SUCCESS."""
        mock_google_op = MagicMock()
        mock_google_op.done = True
        mock_google_op.error.code = 0
        mock_config.google_operations_client.get_operation.return_value = mock_google_op

        op = operations.BuildOperation("op-123")
        assert op.status() == enums.OperationStatus.SUCCESS

    def test_build_operation_status_failure(self, mock_config):
        """Test BuildOperation maps error google op to FAILURE."""
        mock_google_op = MagicMock()
        mock_google_op.done = True
        mock_google_op.error.code = 1
        mock_config.google_operations_client.get_operation.return_value = mock_google_op

        op = operations.BuildOperation("op-123")
        assert op.status() == enums.OperationStatus.FAILURE

    def test_build_operation_in_progress(self, mock_config):
        mock_google_op = MagicMock()
        mock_google_op.done = False
        mock_config.google_operations_client.get_operation.return_value = mock_google_op

        op = operations.BuildOperation("op-123")
        assert op.status() == enums.OperationStatus.IN_PROGRESS

    def test_instance_operation_success(self, mock_config):
        """Test Compute Engine Instance operation success."""
        mock_google_op = MagicMock()
        mock_google_op.done = True
        mock_google_op.error = None

        mock_config.google_zone_operations_client.get.return_value = mock_google_op

        op = operations.InstanceOperation(
            project_id="p1", zone="z1", name="op-instance"
        )
        assert op.status() == enums.OperationStatus.SUCCESS

    def test_instance_operation_failure(self, mock_config):
        """Test Compute Engine Instance operation failure."""
        mock_google_op = MagicMock()
        mock_google_op.done = True
        mock_google_op.error = "Some Error"

        mock_config.google_zone_operations_client.get.return_value = mock_google_op

        op = operations.InstanceOperation(
            project_id="p1", zone="z1", name="op-instance"
        )
        assert op.status() == enums.OperationStatus.FAILURE

    def test_vertex_ai_operation_success(self, mock_config):
        """Test Vertex AI operation success."""
        mock_google_op = MagicMock()
        mock_google_op.done = True
        mock_google_op.error.code = 0

        mock_config.google_cloud_notebooks_operation_client.get_operation.return_value = (
            mock_google_op
        )

        op = operations.VertexAIOperation(name="op-vertex")
        assert op.status() == enums.OperationStatus.SUCCESS
