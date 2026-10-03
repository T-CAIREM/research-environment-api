from datetime import datetime
from typing import Dict, List, Tuple

from research_environment_api.modules.monitoring_management import (
    entities,
    monitoring,
    exceptions,
)
from research_environment_api.web.cache import cache, QUOTAS_CACHE_TIMEOUT
from research_environment_api.modules.app import app
from research_environment_api.modules.workbench_management.entities import (
    MACHINE_TYPE_TO_RESOURCE_MAP,
    MachineType,
)


intervals = (
    ("Days", 86400),  # 60 * 60 * 24
    ("Hours", 3600),  # 60 * 60
    ("Minutes", 60),
    ("Seconds", 1),
)


def stream_workflow_events():
    pubsub = app.config.redis_client.pubsub()
    pubsub.subscribe("workflow_events")
    try:
        while True:
            message = pubsub.get_message(timeout=30)
            if message and message["type"] == "message":
                yield f"event: workflow_update\ndata: {message['data'].decode()}\n\n"
            else:
                yield ": keepalive\n\n"
    finally:
        pubsub.close()


def list_workbench_monitoring_data_entries() -> (
    List[entities.WorkbenchMonitoringDataEntry]
):
    workbench_monitoring_data_entries = (
        monitoring.list_workbench_monitoring_data_entries()
    )

    monitoring_data_to_timestamps = {}
    for entry in workbench_monitoring_data_entries:
        identifier = entities.WorkbenchMonitoringIdentifier(
            user_email=entry.user_email,
            dataset_identifier=entry.dataset_identifier,
            instance_type=entry.instance_type,
        )
        timestamps = (entry.created_at, entry.deleted_at)

        if identifier not in monitoring_data_to_timestamps:
            monitoring_data_to_timestamps[identifier] = []

        monitoring_data_to_timestamps[identifier].append(timestamps)

    serialized_workbench_monitoring_data_entries = [
        entities.WorkbenchMonitoringDataEntry.transform_workbench_monitoring_data(
            identifier, _calculate_total_time(monitoring_data_to_timestamps[identifier])
        )
        for identifier in monitoring_data_to_timestamps.keys()
    ]

    return serialized_workbench_monitoring_data_entries


def get_active_users_per_dataset() -> List[entities.UsersPerDataset]:
    active_workbench_monitoring_data_entries = monitoring.get_active_users_per_dataset()

    return [
        entities.UsersPerDataset(entry.dataset_identifier, entry.user_emails)
        for entry in active_workbench_monitoring_data_entries
    ]


def _calculate_total_time(timestamps: List[Tuple[datetime, datetime]]) -> str:
    now_timestamp = datetime.now()

    # array of tuples (datetime, bool) where bool means if it is beginning or end, True == beginning
    points = [(start, True) for start, _ in timestamps] + [
        (end if end is not None else now_timestamp, False) for _, end in timestamps
    ]

    points.sort()

    total_time = 0
    active_intervals = 0
    interval_start = None

    for timestamp, is_start in points:
        if is_start:
            if active_intervals == 0:
                interval_start = timestamp
            active_intervals += 1
            continue

        active_intervals -= 1
        if active_intervals == 0:
            total_time += (timestamp - interval_start).total_seconds()
            interval_start = None

    return _display_time(total_time)


def _display_time(seconds: float) -> str:
    result = []

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            value = int(value)
            if value == 1:
                name = name.rstrip("s")
            result.append("{} {}".format(value, name))
    return ", ".join(result)


def check_google_quotas(
    base_quota_entity: entities.BaseQuotaMetricsEntity,
    quota_metrics_entity,
    region: str,
) -> List[entities.QuotaInfo]:
    return list(
        _get_quotas_by_metric(
            base_quota_entity.workspace_project_id, quota_metrics_entity, region
        ).values()
    )


def _get_quotas_by_metric(
    project_id: str, quota_metrics_entity, region: str
) -> Dict[entities.ComputeQuotaMetric, entities.QuotaInfo]:
    region_quotas = _get_region_quotas(project_id, region)

    quotas = {}
    for metric in quota_metrics_entity:
        # Metrics the region does not report, or that have no allowance in
        # it, are skipped rather than reported as a zero limit.
        if metric.value not in region_quotas:
            continue
        limit, usage = region_quotas[metric.value]
        if limit <= 0:
            continue
        quotas[metric] = entities.QuotaInfo(
            metric_name=metric.display_name,
            limit=int(limit),
            usage=int(usage),
            region=region,
        )
    return quotas


@cache.memoize(timeout=QUOTAS_CACHE_TIMEOUT)
def _get_region_quotas(project_id: str, region: str) -> Dict[str, Tuple[float, float]]:
    """Returns {quota metric: (limit, usage)} for a project in a Compute region.

    `regions.get` reports the project's effective regional limits (including
    any approved quota adjustments) together with current usage, so a single
    call covers both. A plain dict is returned so the value is cacheable.
    """
    client = app.config.google_compute_engine_regions_client
    compute_region = client.get(project=project_id, region=region)
    return {quota.metric: (quota.limit, quota.usage) for quota in compute_region.quotas}


def clear_quotas_cache(project_id: str, region: str, quota_metrics_entity) -> None:
    # All metrics for a region come from one cached `regions.get` result, so
    # `quota_metrics_entity` does not narrow what is invalidated.
    cache.delete_memoized(_get_region_quotas, project_id, region)


def check_workbench_update_quotas(
    workspace_project_id: str,
    region: str,
    machine_type: MachineType,
    current_machine_type: MachineType,
):
    new_resources = MACHINE_TYPE_TO_RESOURCE_MAP.get(machine_type.value)
    current_resources = MACHINE_TYPE_TO_RESOURCE_MAP.get(current_machine_type.value)
    additional_usage = {
        entities.WorkbenchUpdateQuotaMetricsEntity.CPUS: (
            new_resources.cpu - current_resources.cpu
        ),
    }

    quotas = _get_quotas_by_metric(
        workspace_project_id, entities.WorkbenchUpdateQuotaMetricsEntity, region
    )
    for metric, additional in additional_usage.items():
        quota = quotas.get(metric)
        if quota is None:
            continue
        estimated_usage = quota.usage + additional
        if quota.limit < estimated_usage:
            raise exceptions.QuotaExceededError(
                f"Quota {quota.metric_name} has been exceeded - estimated usage: {estimated_usage}, when limit is {quota.limit}"
            )
