from dataclasses import dataclass, field


@dataclass
class WorkbenchMonitoringDataEntry:
    user_email: str
    dataset_identifier: str
    instance_type: str
    total_time: str

    @classmethod
    def transform_workbench_monitoring_data(cls, key, total_time):
        user_email = key[0]
        dataset_identifier = key[1]
        instance_type = key[2]

        return cls(
            user_email=user_email,
            dataset_identifier=dataset_identifier,
            instance_type=instance_type.value,
            total_time=total_time,
        )
