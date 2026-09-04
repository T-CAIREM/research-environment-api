from pathlib import Path

import pytest
from marshmallow import ValidationError


# create_app() regenerates the checked-in swagger spec on every boot. Under the
# unit-test mocks the machine-type enum collapses to the single fake machine
# type, so the regenerated file must not be left behind.
SWAGGER_SPEC = Path(__file__).resolve().parents[3] / "web" / "static" / "swagger.json"
# Snapshotted at collection time, i.e. before any test can boot the app.
SWAGGER_SPEC_ORIGINAL = SWAGGER_SPEC.read_bytes() if SWAGGER_SPEC.exists() else None


BASE_CREATE_BODY = {
    "workbench_type": "jupyter",
    "workspace_project_id": "proj-1",
    "user_email": "user@test.com",
    "dataset_identifier": "ds-1",
    "bucket_name": "b-1",
    "machine_type": "n1-standard-1",
    "memory": 3.75,
    "cpu": 1,
    "disk_size": 100,
    "user_groups": [],
    "region": "us-central1",
}


@pytest.fixture
def preserve_swagger_spec():
    """Restore the checked-in swagger spec after the app has rewritten it."""
    yield

    if SWAGGER_SPEC_ORIGINAL is None:
        SWAGGER_SPEC.unlink(missing_ok=True)
    else:
        SWAGGER_SPEC.write_bytes(SWAGGER_SPEC_ORIGINAL)


@pytest.fixture
def schemas(preserve_swagger_spec, app):
    """Import the schemas through the `app` fixture.

    `web.workbench_management.__init__` pulls in the views, which reach the
    celery worker module and initialize the real config (GCP clients, DB
    engine) at import time. The `app` fixture has those patched, so importing
    here keeps the import side effects mocked.
    """
    from research_environment_api.web.workbench_management import schemas

    return schemas


class TestWorkbenchCreateRequestSchema:
    def test_writable_defaults_to_false_when_absent(self, schemas):
        """Published requests do not send the key at all and stay read-only."""
        loaded = schemas.WorkbenchCreateRequest().load(BASE_CREATE_BODY)

        assert loaded["writable"] is False
        assert loaded["object_prefix"] == ""

    def test_writable_is_loaded_when_true(self, schemas):
        """The portal only sends writable=true, and only for draft mounts."""
        loaded = schemas.WorkbenchCreateRequest().load(
            {
                **BASE_CREATE_BODY,
                "object_prefix": "active-projects/my-draft",
                "writable": True,
            }
        )

        assert loaded["writable"] is True
        assert loaded["object_prefix"] == "active-projects/my-draft"

    def test_writable_rejects_non_boolean(self, schemas):
        with pytest.raises(ValidationError):
            schemas.WorkbenchCreateRequest().load(
                {**BASE_CREATE_BODY, "writable": "yes-please"}
            )


class TestWorkbenchResponseSchema:
    def test_mount_fields_are_additive(self, schemas):
        """The portal badges draft mounts from these keys; both are optional."""
        fields = schemas.Workbench().fields

        assert "writable" in fields
        assert "object_prefix" in fields
        assert fields["writable"].required is False
        assert fields["object_prefix"].required is False

    def test_mount_fields_are_dumped(self, schemas):
        dumped = schemas.Workbench(only=("writable", "object_prefix")).dump(
            {"writable": True, "object_prefix": "active-projects/my-draft"}
        )

        assert dumped == {
            "writable": True,
            "object_prefix": "active-projects/my-draft",
        }
