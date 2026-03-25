from datetime import datetime
import time
from typing import List, Tuple

from google.cloud import monitoring_v3, service_usage_v1, billing_v1
from google.cloud.service_usage_v1.types import resources

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
    project_id = base_quota_entity.workspace_project_id
    service_info = _get_service_info(project_id)
    quotas_to_list = [metric.value for metric in quota_metrics_entity]

    return [
        entities.QuotaInfo(
            metric_name=limit.display_name,
            limit=limit.values["DEFAULT"],
            usage=_get_current_metric_usage(project_id, region, limit.metric),
            region=region,
        )
        for limit in service_info.config.quota.limits
        if limit.metric in quotas_to_list and limit.values["DEFAULT"] > 0
    ]


@cache.memoize(timeout=QUOTAS_CACHE_TIMEOUT)
def _get_service_info(project_id: str) -> resources.Service:
    client = app.config.google_service_usage_client
    service_name = f"projects/{project_id}/services/compute.googleapis.com"

    request = service_usage_v1.GetServiceRequest(name=service_name)
    return client.get_service(request=request)


@cache.memoize(timeout=QUOTAS_CACHE_TIMEOUT)
def _get_current_metric_usage(project_id: str, region: str, metric: str) -> int:
    client = app.config.google_metric_service_client

    # Query current usage for the given metric
    project_name = f"projects/{project_id}"
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": int(time.time())},
            "start_time": {"seconds": int(time.time()) - 604800},  # one week
        }
    )
    aggregation = monitoring_v3.Aggregation(
        alignment_period={"seconds": 60},
        cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
        per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_NEXT_OLDER,
    )
    request = monitoring_v3.ListTimeSeriesRequest(
        name=project_name,
        filter=_build_filter(project_id, region, metric),
        interval=interval,
        aggregation=aggregation,
        view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
    )

    client.list_time_series(request)
    results = list(client.list_time_series(request))

    return 0 if len(results) == 0 else results[0].points[0].value.int64_value


def _build_filter(project_id: str, region: str, metric: str) -> str:
    return (
        'resource.type="consumer_quota" AND '
        'metric.type="serviceruntime.googleapis.com/quota/allocation/usage" AND '
        f'resource.label.project_id="{project_id}" AND '
        'resource.label.service="compute.googleapis.com" AND '
        f'metric.label.quota_metric="{metric}" AND '
        f'resource.label.location="{region}"'
    )


def clear_quotas_cache(project_id: str, region: str, quota_metrics_entity) -> None:
    for metric in quota_metrics_entity:
        cache.delete_memoized(
            _get_current_metric_usage, project_id, region, metric.value
        )
    cache.delete_memoized(_get_service_info, project_id)


def check_workbench_update_quotas(
    workspace_project_id: str, region: str, machine_type: MachineType
):
    base_quota_metrics_entity = entities.BaseQuotaMetricsEntity(
        workspace_project_id=workspace_project_id
    )
    quotas = check_google_quotas(
        base_quota_metrics_entity, entities.WorkbenchUpdateQuotaMetricsEntity, region
    )
    machine_resources = MACHINE_TYPE_TO_RESOURCE_MAP.get(machine_type.value)
    additional_quotas_dict = {"CPUs": machine_resources.cpu}
    for quota in quotas:
        estimated_usage = quota.usage + additional_quotas_dict[quota.metric_name]
        if quota.limit < estimated_usage:
            raise exceptions.QuotaExceededError(
                f"Quota {quota.metric_name} has been exceeded - estimated usage: {estimated_usage}, when limit is {quota.limit}"
            )
