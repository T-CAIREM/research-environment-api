import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from research_environment_api.modules.monitoring_management import (
    services,
    entities,
    exceptions,
)


class TestMonitoringServices:
    """Test monitoring logic including time calculations and quota checks."""

    def test_calculate_total_time_simple_interval(self):
        """Test calculating duration for a single completed session."""
        start = datetime(2023, 1, 1, 10, 0, 0)
        end = datetime(2023, 1, 1, 12, 0, 0)  # 2 hours
        timestamps = [(start, end)]

        with patch(
            "research_environment_api.modules.monitoring_management.services.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime(2023, 1, 2, 0, 0, 0)
            result = services._calculate_total_time(timestamps)

        assert result == "2 Hours"

    def test_calculate_total_time_active_session(self):
        """Test calculating duration for a session that is still active (None end time)."""
        start = datetime(2023, 1, 1, 10, 0, 0)
        # "Now" is 11:00:00 -> 1 hour duration
        now_mock = datetime(2023, 1, 1, 11, 0, 0)
        timestamps = [(start, None)]

        with patch(
            "research_environment_api.modules.monitoring_management.services.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = now_mock
            result = services._calculate_total_time(timestamps)

        assert result == "1 Hour"

    def test_calculate_total_time_complex_overlap(self):
        """Test logic for multiple sessions."""
        t1_start = datetime(2023, 1, 1, 11, 0, 0)
        t1_end = datetime(2023, 1, 1, 11, 30, 0)
        t2_start = datetime(2023, 1, 1, 11, 0, 0)
        t2_end = datetime(2023, 1, 1, 12, 30, 0)
        timestamps = [(t1_start, t1_end), (t2_start, t2_end)]

        with patch(
            "research_environment_api.modules.monitoring_management.services.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime(2023, 1, 2)
            result = services._calculate_total_time(timestamps)

        # 1.5 hours -> 1 Hour, 30 Minutes
        assert "1 Hour" in result
        assert "30 Minutes" in result

    def test_check_google_quotas(self, mocker, mock_config):
        """Test retrieving and checking quotas against limits."""
        # Arrange
        mock_service_info = MagicMock()
        mock_limit = MagicMock()
        mock_limit.metric = "compute.googleapis.com/cpus"
        mock_limit.display_name = "CPUs"
        mock_limit.values = {"DEFAULT": 100}
        mock_service_info.config.quota.limits = [mock_limit]

        mocker.patch(
            "research_environment_api.modules.monitoring_management.services._get_service_info",
            return_value=mock_service_info,
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services._get_current_metric_usage",
            return_value=10,
        )

        base_entity = MagicMock(workspace_project_id="test-proj")
        metric_enum = MagicMock()
        metric_enum.value = "compute.googleapis.com/cpus"
        quota_metrics = [metric_enum]

        # Act
        results = services.check_google_quotas(
            base_entity, quota_metrics, "us-central1"
        )

        # Assert
        assert len(results) == 1
        assert results[0].metric_name == "CPUs"
        assert results[0].limit == 100
        assert results[0].usage == 10

    def test_check_workbench_update_quotas_exceeded(self, mocker):
        """Test that QuotaExceededError is raised when usage - current_cpu + new_cpu > limit."""
        # Arrange
        quota_info = entities.QuotaInfo(
            metric_name="CPUs", limit=10, usage=8, region="us-central1"
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.check_google_quotas",
            return_value=[quota_info],
        )

        mock_new_machine = MagicMock()
        mock_new_machine.value = "n1-standard-4"
        mock_current_machine = MagicMock()
        mock_current_machine.value = "n1-standard-1"

        # Patch the resource map dictionary in services module
        mocker.patch.dict(
            "research_environment_api.modules.monitoring_management.services.MACHINE_TYPE_TO_RESOURCE_MAP",
            {
                "n1-standard-4": MagicMock(cpu=4),
                "n1-standard-1": MagicMock(cpu=1),
            },
        )

        # Act & Assert
        # 8 (usage) - 1 (current) + 4 (new) = 11 > 10 (limit) -> Error
        with pytest.raises(exceptions.QuotaExceededError):
            services.check_workbench_update_quotas(
                "proj", "region", mock_new_machine, mock_current_machine
            )

    def test_check_workbench_update_quotas_not_exceeded_when_replacing(self, mocker):
        """Test that no error is raised when replacing an instance stays within limit."""
        # Arrange: limit=32, usage=2 (current 2-CPU instance), upgrading to 32-CPU machine
        quota_info = entities.QuotaInfo(
            metric_name="CPUs", limit=32, usage=2, region="us-central1"
        )
        mocker.patch(
            "research_environment_api.modules.monitoring_management.services.check_google_quotas",
            return_value=[quota_info],
        )

        mock_new_machine = MagicMock()
        mock_new_machine.value = "n1-standard-32"
        mock_current_machine = MagicMock()
        mock_current_machine.value = "n1-standard-2"

        mocker.patch.dict(
            "research_environment_api.modules.monitoring_management.services.MACHINE_TYPE_TO_RESOURCE_MAP",
            {
                "n1-standard-32": MagicMock(cpu=32),
                "n1-standard-2": MagicMock(cpu=2),
            },
        )

        # Act & Assert
        # 2 (usage) - 2 (current) + 32 (new) = 32, 32 < 32 is False -> no error
        services.check_workbench_update_quotas(
            "proj", "region", mock_new_machine, mock_current_machine
        )
