from datetime import datetime
from typing import List, Tuple

from research_environment_api.modules.monitoring_management import entities, monitoring

intervals = (
    ("Days", 86400),  # 60 * 60 * 24
    ("Hours", 3600),  # 60 * 60
    ("Minutes", 60),
    ("Seconds", 1),
)


def list_workbench_monitoring_data_entries() -> (
    List[entities.WorkbenchMonitoringDataEntry]
):
    workbench_monitoring_data_entries = (
        monitoring.list_workbench_monitoring_data_entries()
    )

    monitoring_data_to_timestamps = {}
    for entry in workbench_monitoring_data_entries:
        key = (entry.user_email, entry.dataset_identifier, entry.instance_type)
        timestamps = (entry.created_at, entry.deleted_at)

        if key not in monitoring_data_to_timestamps:
            monitoring_data_to_timestamps[key] = []

        monitoring_data_to_timestamps[key].append(timestamps)

    serialized_workbench_monitoring_data_entries = [
        entities.WorkbenchMonitoringDataEntry.transform_workbench_monitoring_data(
            key, _calculate_total_time(monitoring_data_to_timestamps[key])
        )
        for key in monitoring_data_to_timestamps.keys()
    ]

    return serialized_workbench_monitoring_data_entries


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
