from research_environment_api.modules.monitoring_management import entities, monitoring


def list_workbench_monitoring_data_entries():
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
            key, timestamps
        )
        for key, timestamps in monitoring_data_to_timestamps.items()
    ]

    return serialized_workbench_monitoring_data_entries
