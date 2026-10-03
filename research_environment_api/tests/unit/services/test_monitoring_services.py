import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from google.cloud import compute_v1
from research_environment_api.modules.monitoring_management import (
    services,
    entities,
    exceptions,
)


def _region(quotas):
    """Builds a Compute `Region` carrying {metric: (limit, usage)} quotas."""
    return compute_v1.Region(
        quotas=[
            compute_v1.Quota(metric=metric, limit=limit, usage=usage)
            for metric, (limit, usage) in quotas.items()
        ]
    )


class TestMonitoringServices:
    """Test monitoring logic including time calculations and quota checks.

    Quota tests request the `app` fixture: the regions lookup is memoized via
    Flask-Caching, which needs an application context (pushed by pytest-flask).
    """

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

    def test_check_google_quotas(self, app, mock_config):
        """Effective regional limits and usage come from Compute `regions.get`."""
        # Arrange
        regions_client = mock_config.google_compute_engine_regions_client
        regions_client.get.return_value = _region(
            {
                "CPUS": (5000.0, 20.0),
                "NVIDIA_T4_GPUS": (4.0, 1.0),
                "INSTANCES": (6000.0, 3.0),
                "IN_USE_ADDRESSES": (575.0, 2.0),
                "DISKS_TOTAL_GB": (102400.0, 350.0),
                "SSD_TOTAL_GB": (2048.0, 0.0),  # not requested -> ignored
            }
        )
        base_entity = entities.BaseQuotaMetricsEntity(workspace_project_id="test-proj")

        # Act
        results = services.check_google_quotas(
            base_entity, entities.GeneralQuotaMetrics, "us-central1"
        )

        # Assert
        regions_client.get.assert_called_once_with(
            project="test-proj", region="us-central1"
        )
        by_name = {quota.metric_name: quota for quota in results}
        assert set(by_name) == {
            "CPUs",
            "NVIDIA T4 GPUs",
            "VM instances",
            "In-use IP addresses",
            "Persistent disk total (GB)",
        }
        cpus = by_name["CPUs"]
        assert (cpus.limit, cpus.usage, cpus.region) == (5000, 20, "us-central1")
        assert isinstance(cpus.limit, int) and isinstance(cpus.usage, int)

    def test_check_google_quotas_skips_metrics_missing_from_region(
        self, app, mock_config
    ):
        """Metrics absent from the region response (or with no allowance) are skipped."""
        # Arrange
        mock_config.google_compute_engine_regions_client.get.return_value = _region(
            {"CPUS": (5000.0, 20.0), "NVIDIA_T4_GPUS": (0.0, 0.0)}
        )
        base_entity = entities.BaseQuotaMetricsEntity(workspace_project_id="test-proj")

        # Act
        results = services.check_google_quotas(
            base_entity, entities.GeneralQuotaMetrics, "europe-west3"
        )

        # Assert
        assert results == [
            entities.QuotaInfo(
                metric_name="CPUs", limit=5000, usage=20, region="europe-west3"
            )
        ]

    def test_clear_quotas_cache_deletes_region_entry(self, mocker):
        """Clearing drops the memoized `regions.get` result for that project/region."""
        delete_memoized = mocker.patch.object(services.cache, "delete_memoized")

        services.clear_quotas_cache(
            "test-proj", "us-central1", entities.GeneralQuotaMetrics
        )

        delete_memoized.assert_called_once_with(
            services._get_region_quotas, "test-proj", "us-central1"
        )

    def test_check_workbench_update_quotas_exceeded(self, app, mocker, mock_config):
        """Test that QuotaExceededError is raised when usage - current_cpu + new_cpu > limit."""
        # Arrange
        mock_config.google_compute_engine_regions_client.get.return_value = _region(
            {"CPUS": (10.0, 8.0)}
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
        with pytest.raises(exceptions.QuotaExceededError) as exc_info:
            services.check_workbench_update_quotas(
                "proj", "region", mock_new_machine, mock_current_machine
            )
        assert str(exc_info.value) == (
            "Quota CPUs has been exceeded - estimated usage: 11, when limit is 10"
        )

    def test_check_workbench_update_quotas_not_exceeded_when_replacing(
        self, app, mocker, mock_config
    ):
        """Test that no error is raised when replacing an instance stays within limit."""
        # Arrange: limit=32, usage=2 (current 2-CPU instance), upgrading to 32-CPU machine
        mock_config.google_compute_engine_regions_client.get.return_value = _region(
            {"CPUS": (32.0, 2.0)}
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

    def test_check_workbench_update_quotas_uses_effective_regional_limit(
        self, app, mocker, mock_config
    ):
        """A 16 -> 64 CPU resize fits a 5000-CPU regional limit with 20 CPUs in use."""
        # Arrange
        regions_client = mock_config.google_compute_engine_regions_client
        regions_client.get.return_value = _region(
            {"CPUS": (5000.0, 20.0), "INSTANCES": (6000.0, 3.0)}
        )

        mock_new_machine = MagicMock()
        mock_new_machine.value = "n1-standard-64"
        mock_current_machine = MagicMock()
        mock_current_machine.value = "n1-standard-16"

        mocker.patch.dict(
            "research_environment_api.modules.monitoring_management.services.MACHINE_TYPE_TO_RESOURCE_MAP",
            {
                "n1-standard-64": MagicMock(cpu=64),
                "n1-standard-16": MagicMock(cpu=16),
            },
        )

        # Act & Assert
        # 20 (usage) - 16 (current) + 64 (new) = 68 <= 5000 (limit) -> no error
        services.check_workbench_update_quotas(
            "test-proj", "us-central1", mock_new_machine, mock_current_machine
        )
        regions_client.get.assert_called_once_with(
            project="test-proj", region="us-central1"
        )
