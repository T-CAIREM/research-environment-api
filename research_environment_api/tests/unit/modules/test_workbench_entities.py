from unittest.mock import MagicMock

from research_environment_api.modules.workbench_management import entities


def _metadata_item(key, value):
    item = MagicMock()
    item.key = key
    item.value = value
    return item


def _gce_instance(metadata: dict):
    instance = MagicMock()
    instance.name = "jupyter-wb-1"
    instance.id = "123"
    instance.status = "RUNNING"
    instance.zone = "projects/p/zones/us-central1-a"
    instance.machine_type = "projects/p/zones/us-central1-a/machineTypes/n1-standard-1"
    instance.guest_accelerators = []
    instance.disks = [MagicMock(disk_size_gb=100)]
    instance.labels = {}
    instance.metadata.items = [_metadata_item(k, v) for k, v in metadata.items()]
    return instance


BASE_METADATA = {
    "dataset_identifier": "ds-1",
    "bucket_name": "b-1",
    "vm_image": "img-1",
    "service_account_name": "sa-1",
    "type": "jupyter",
}


class TestWorkbenchCreate:
    def _create(self, **overrides):
        kwargs = dict(
            workbench_type="jupyter",
            workspace_project_id="proj-1",
            user_email="user@test.com",
            workspace_numeric_id="123",
            machine_type="n1-standard-1",
            memory=3.75,
            cpu=1,
            disk_size=100,
            region="us-central1",
            dataset_identifier="ds-1",
            bucket_name="b-1",
            user_groups=[],
        )
        kwargs.update(overrides)
        return entities.WorkbenchCreate(**kwargs)

    def test_defaults_reproduce_published_behaviour(self):
        request = self._create()

        assert request.writable is False
        assert request.object_prefix == ""
        # The pinned image name is untouched by the family override.
        assert request.vm_image == "workbench-instances-v20240214"

    def test_vm_image_family_comes_from_config(self):
        """Set once in config so a rollback is an env var change, not a deploy."""
        request = self._create()

        assert request.vm_image_family == "workbench-instances"

    def test_writable_draft_mount(self):
        request = self._create(object_prefix="active-projects/my-draft", writable=True)

        assert request.writable is True
        assert request.object_prefix == "active-projects/my-draft"


class TestWorkbenchFromGceInstance:
    def test_missing_mount_metadata_defaults_to_published(self):
        """Workbenches created before draft mounts existed carry no such keys."""
        workbench = entities.Workbench.from_gce_instance(
            _gce_instance(BASE_METADATA), []
        )

        assert workbench.object_prefix == ""
        assert workbench.writable is False

    def test_draft_mount_metadata_is_read_back(self):
        """Destroy rebuilds its terraform inputs from instance metadata."""
        workbench = entities.Workbench.from_gce_instance(
            _gce_instance(
                {
                    **BASE_METADATA,
                    "object_prefix": "active-projects/my-draft",
                    "writable": "true",
                }
            ),
            [],
        )

        assert workbench.object_prefix == "active-projects/my-draft"
        assert workbench.writable is True

    def test_writable_metadata_is_only_true_for_the_literal_string(self):
        workbench = entities.Workbench.from_gce_instance(
            _gce_instance(
                {
                    **BASE_METADATA,
                    "object_prefix": "active-projects/my-draft",
                    "writable": "false",
                }
            ),
            [],
        )

        assert workbench.writable is False
