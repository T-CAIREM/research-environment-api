import json
from unittest.mock import MagicMock
import pytest

from research_environment_api.background import builds
from research_environment_api.modules.workbench_management.entities import (
    MachineType,
    Region,
    WorkbenchType,
)


COMMON_EXPECTED_VALUES = {
    "workspace_project_id": "proj-1",
    "region": Region.US_CENTRAL,
    "zone": "us-central1-a",
    "machine_type": MachineType.N1_STANDARD_1,
    "disk_size": 100,
    "dataset_identifier": "ds-1",
    "user_email": "user@test.com",
    "bucket_name": "b-1",
}


def _assert_common_substitutions(subs, expected_values, include_organization_id=True):
    """Assert common substitutions that are shared across all build types."""
    assert subs["_PROJECT_ID"] == expected_values["workspace_project_id"]
    assert subs["_REGION"] == expected_values["region"].value
    assert subs["_ZONE"] == expected_values["zone"]
    assert subs["_MACHINE_TYPE"] == expected_values["machine_type"].value
    assert subs["_DISK_SIZE"] == str(expected_values["disk_size"])
    assert subs["_DATASET"] == expected_values["dataset_identifier"]
    assert subs["_EMAIL_ID"] == expected_values["user_email"]
    assert subs["_BUCKET_NAME"] == expected_values["bucket_name"]
    assert subs["_INSTANCE_NAME"] == expected_values["instance_name"]
    assert subs["_SERVICE_ACCOUNT_NAME"] == expected_values["service_account_name"]
    assert subs["_TERRAFORM_REPO_NAME"] == "tf-repo"
    assert subs["_TERRAFORM_BRANCH_NAME"] == "main"
    if include_organization_id:
        assert subs["_ORGANIZATION_ID"] == "org-123"
    assert subs["_ASSOCIATED_EVENT"] == expected_values["associated_event"]


def _assert_build_configuration(build):
    """Assert basic build configuration."""
    assert len(build.steps) > 0
    assert build.service_account == "projects/my-project/serviceAccounts/my-sa"


def _assert_jupyter_like_substitutions(
    subs, gpu_accelerator, vm_image, sharing_dict, permissions_list, collaborative
):
    """Assert substitutions common to Jupyter and Collaborative workbenches."""
    assert subs["_JUPYTER_STATE_BUCKET"] == "test-jupyter-states"
    assert subs["_GPU_ACCELERATOR"] == gpu_accelerator
    assert subs["_VM_IMAGE"] == vm_image
    assert subs["_JUPYTER_STARTUP_SCRIPT_BUCKET"] == "gs://script"
    assert subs["_SHARING_BUCKET_IDENTIFIERS"] == ",".join(sharing_dict.keys())
    assert subs["_SHARING_BUCKET_PERMISSIONS"] == ",".join(sharing_dict.values())
    assert subs["_USER_PERMISSIONS_LIST"] == ",".join(permissions_list)
    assert subs["_COLLABORATIVE"] == collaborative


class TestBuilds:
    @pytest.fixture
    def common_config_setup(self, mock_config):
        """Common configuration setup for all build tests."""
        mock_config.cloud_build_service_account_name = (
            "projects/my-project/serviceAccounts/my-sa"
        )
        mock_config.github_ssh_key_ksm_id = (
            "projects/my-project/secrets/my-secret/versions/1"
        )
        mock_config.organization_id = "org-123"
        mock_config.terraform_repo_name = "tf-repo"
        mock_config.terraform_branch_name = "main"
        return mock_config

    def test_create_jupyter_workbench_build_substitutions(self, common_config_setup):
        """Verify that all Terraform variables are correctly populated."""
        # Arrange
        mock_config = common_config_setup
        mock_config.jupyter_startup_script = "gs://script"

        expected_values = {
            **COMMON_EXPECTED_VALUES,
            "instance_name": "wb-1",
            "service_account_name": "sa-1",
            "associated_event": "test-event-123",
        }

        sharing_dict = {"shared-1": "READ"}
        permissions_list = ["roles/viewer"]

        # Act
        build = builds.create_jupyter_workbench_build(
            workspace_project_id=expected_values["workspace_project_id"],
            region=expected_values["region"],
            zone=expected_values["zone"],
            machine_type=expected_values["machine_type"],
            disk_size=expected_values["disk_size"],
            instance_name=expected_values["instance_name"],
            service_account_name=expected_values["service_account_name"],
            gpu_accelerator_type="NVIDIA_TESLA_T4",
            dataset_identifier=expected_values["dataset_identifier"],
            user_email=expected_values["user_email"],
            bucket_name=expected_values["bucket_name"],
            vm_image="img-1",
            sharing_bucket_permission_dict=sharing_dict,
            user_permissions_list=permissions_list,
            collaborative="true",
            associated_event=expected_values["associated_event"],
        )

        # Assert
        subs = build.substitutions
        _assert_common_substitutions(subs, expected_values)
        _assert_jupyter_like_substitutions(
            subs, "NVIDIA_TESLA_T4", "img-1", sharing_dict, permissions_list, "true"
        )
        assert subs["_WORKBENCH_TYPE"] == WorkbenchType.JUPYTER
        assert subs["_OBJECT_PREFIX"] == ""
        # Defaults must reproduce today's behaviour: read-only mount, pinned
        # vm_image (no image family override).
        assert subs["_WRITABLE"] == "false"
        assert subs["_VM_IMAGE_FAMILY"] == ""
        _assert_build_configuration(build)

    def test_create_jupyter_workbench_build_object_prefix(self, common_config_setup):
        """Verify that an object prefix is passed to the build as a substitution."""
        # Arrange
        mock_config = common_config_setup
        mock_config.jupyter_startup_script = "gs://script"

        # Act
        build = builds.create_jupyter_workbench_build(
            workspace_project_id=COMMON_EXPECTED_VALUES["workspace_project_id"],
            region=COMMON_EXPECTED_VALUES["region"],
            zone=COMMON_EXPECTED_VALUES["zone"],
            machine_type=COMMON_EXPECTED_VALUES["machine_type"],
            disk_size=COMMON_EXPECTED_VALUES["disk_size"],
            instance_name="wb-1",
            service_account_name="sa-1",
            gpu_accelerator_type=None,
            dataset_identifier=COMMON_EXPECTED_VALUES["dataset_identifier"],
            user_email=COMMON_EXPECTED_VALUES["user_email"],
            bucket_name=COMMON_EXPECTED_VALUES["bucket_name"],
            vm_image="img-1",
            sharing_bucket_permission_dict={},
            user_permissions_list=[],
            collaborative="false",
            associated_event=None,
            object_prefix="active-projects/my-draft",
        )

        # Assert
        assert build.substitutions["_OBJECT_PREFIX"] == "active-projects/my-draft"
        assert build.substitutions["_WRITABLE"] == "false"

    def test_create_jupyter_workbench_build_writable(self, common_config_setup):
        """A writable draft mount sends _WRITABLE=true and the VM image family."""
        # Arrange
        mock_config = common_config_setup
        mock_config.jupyter_startup_script = "gs://script"

        # Act
        build = builds.create_jupyter_workbench_build(
            workspace_project_id=COMMON_EXPECTED_VALUES["workspace_project_id"],
            region=COMMON_EXPECTED_VALUES["region"],
            zone=COMMON_EXPECTED_VALUES["zone"],
            machine_type=COMMON_EXPECTED_VALUES["machine_type"],
            disk_size=COMMON_EXPECTED_VALUES["disk_size"],
            instance_name="wb-1",
            service_account_name="sa-1",
            gpu_accelerator_type=None,
            dataset_identifier=COMMON_EXPECTED_VALUES["dataset_identifier"],
            user_email=COMMON_EXPECTED_VALUES["user_email"],
            bucket_name=COMMON_EXPECTED_VALUES["bucket_name"],
            vm_image="img-1",
            sharing_bucket_permission_dict={},
            user_permissions_list=[],
            collaborative="false",
            associated_event=None,
            object_prefix="active-projects/my-draft",
            writable=True,
            vm_image_family="workbench-instances",
        )

        # Assert
        subs = build.substitutions
        assert subs["_OBJECT_PREFIX"] == "active-projects/my-draft"
        # Cloud Build substitutions are strings; terraform parses "true"/"false"
        # into var.writable (bool).
        assert subs["_WRITABLE"] == "true"
        assert subs["_VM_IMAGE_FAMILY"] == "workbench-instances"
        # The pinned image name is still sent; terraform picks the family when
        # the family is non-empty.
        assert subs["_VM_IMAGE"] == "img-1"

    def test_create_jupyter_workbench_build_ensures_managed_folder(
        self, common_config_setup
    ):
        """The managed folder is created before terraform binds IAM to it."""
        # Arrange
        mock_config = common_config_setup
        mock_config.jupyter_startup_script = "gs://script"

        # Act
        build = builds.create_jupyter_workbench_build(
            workspace_project_id=COMMON_EXPECTED_VALUES["workspace_project_id"],
            region=COMMON_EXPECTED_VALUES["region"],
            zone=COMMON_EXPECTED_VALUES["zone"],
            machine_type=COMMON_EXPECTED_VALUES["machine_type"],
            disk_size=COMMON_EXPECTED_VALUES["disk_size"],
            instance_name="wb-1",
            service_account_name="sa-1",
            gpu_accelerator_type=None,
            dataset_identifier=COMMON_EXPECTED_VALUES["dataset_identifier"],
            user_email=COMMON_EXPECTED_VALUES["user_email"],
            bucket_name=COMMON_EXPECTED_VALUES["bucket_name"],
            vm_image="img-1",
            sharing_bucket_permission_dict={},
            user_permissions_list=[],
            collaborative="false",
            associated_event=None,
            object_prefix="active-projects/my-draft",
            writable=True,
        )

        # Assert
        step_ids = [step.id for step in build.steps]
        assert "jupyter_workbench_creation_ensure_managed_folder" in step_ids
        assert step_ids.index(
            "jupyter_workbench_creation_ensure_managed_folder"
        ) < step_ids.index("jupyter_workbench_creation_terraform_init")

        ensure_step = next(
            step
            for step in build.steps
            if step.id == "jupyter_workbench_creation_ensure_managed_folder"
        )
        script = ensure_step.args[1]
        assert "managed-folders describe" in script
        assert "managed-folders create" in script
        # Trailing slash is required by GCS for managed folder names.
        assert 'gs://${_BUCKET_NAME}/${_OBJECT_PREFIX}/"' in script

        # python4.py receives writable as its 5th positional argument.
        set_config_step = next(
            step
            for step in build.steps
            if step.id == "jupyter_workbench_creation_set_config"
        )
        assert list(set_config_step.args)[-2:] == [
            "${_OBJECT_PREFIX}",
            "${_WRITABLE}",
        ]

        plan_step = next(
            step
            for step in build.steps
            if step.id == "jupyter_workbench_creation_terraform_plan"
        )
        assert "TF_VAR_object_prefix=${_OBJECT_PREFIX}" in plan_step.env
        assert "TF_VAR_writable=${_WRITABLE}" in plan_step.env
        assert "TF_VAR_vm_image_family=${_VM_IMAGE_FAMILY}" in plan_step.env

    def test_destroy_jupyter_workbench_build_substitutions(self, common_config_setup):
        """Destroy defaults reproduce today's behaviour (no prefix, read-only)."""
        # Arrange
        mock_config = common_config_setup
        mock_config.jupyter_startup_script = "gs://script"

        # Act
        build = builds.destroy_jupyter_workbench_build(
            workspace_project_id=COMMON_EXPECTED_VALUES["workspace_project_id"],
            region=COMMON_EXPECTED_VALUES["region"],
            zone=COMMON_EXPECTED_VALUES["zone"],
            machine_type=COMMON_EXPECTED_VALUES["machine_type"],
            disk_size=COMMON_EXPECTED_VALUES["disk_size"],
            gpu_accelerator_type=None,
            dataset_identifier=COMMON_EXPECTED_VALUES["dataset_identifier"],
            user_email=COMMON_EXPECTED_VALUES["user_email"],
            bucket_name=COMMON_EXPECTED_VALUES["bucket_name"],
            vm_image="img-1",
            instance_name="wb-1",
            service_account_name="sa-1",
            sharing_bucket_identifiers=[],
            collaborative="false",
        )

        # Assert
        subs = build.substitutions
        assert subs["_OBJECT_PREFIX"] == ""
        assert subs["_WRITABLE"] == "false"

        destroy_step = next(
            step
            for step in build.steps
            if step.id == "jupyter_workbench_destruction_terraform_destroy"
        )
        assert "TF_VAR_object_prefix=${_OBJECT_PREFIX}" in destroy_step.env
        assert "TF_VAR_writable=${_WRITABLE}" in destroy_step.env
        _assert_build_configuration(build)

    def test_destroy_jupyter_workbench_build_carries_draft_mount(
        self, common_config_setup
    ):
        """Destroy rebuilds the mount inputs from instance metadata.

        RE-API keeps no per-workbench record, so the prefix and mode read off
        the GCE instance have to be replayed as TF_VARs or terraform would plan
        a diff instead of a clean destroy.
        """
        # Arrange
        mock_config = common_config_setup
        mock_config.jupyter_startup_script = "gs://script"

        # Act
        build = builds.destroy_jupyter_workbench_build(
            workspace_project_id=COMMON_EXPECTED_VALUES["workspace_project_id"],
            region=COMMON_EXPECTED_VALUES["region"],
            zone=COMMON_EXPECTED_VALUES["zone"],
            machine_type=COMMON_EXPECTED_VALUES["machine_type"],
            disk_size=COMMON_EXPECTED_VALUES["disk_size"],
            gpu_accelerator_type=None,
            dataset_identifier=COMMON_EXPECTED_VALUES["dataset_identifier"],
            user_email=COMMON_EXPECTED_VALUES["user_email"],
            bucket_name=COMMON_EXPECTED_VALUES["bucket_name"],
            vm_image="img-1",
            instance_name="wb-1",
            service_account_name="sa-1",
            sharing_bucket_identifiers=[],
            collaborative="false",
            object_prefix="active-projects/my-draft",
            writable=True,
        )

        # Assert
        subs = build.substitutions
        assert subs["_OBJECT_PREFIX"] == "active-projects/my-draft"
        assert subs["_WRITABLE"] == "true"

    def test_create_collaborative_workbench_build_substitutions(
        self, common_config_setup
    ):
        """Verify that all Terraform variables are correctly populated for collaborative workbench."""
        # Arrange
        mock_config = common_config_setup
        mock_config.jupyter_startup_script = "gs://script"

        expected_values = {
            **COMMON_EXPECTED_VALUES,
            "instance_name": "collab-wb-1",
            "service_account_name": "sa-1",
            "associated_event": "test-event-789",
        }

        sharing_dict = {"shared-1": "READ", "shared-2": "WRITE"}
        permissions_list = ["roles/viewer", "roles/editor"]

        # Act
        build = builds.create_collaborative_workbench_build(
            workspace_project_id=expected_values["workspace_project_id"],
            region=expected_values["region"],
            zone=expected_values["zone"],
            machine_type=expected_values["machine_type"],
            disk_size=expected_values["disk_size"],
            instance_name=expected_values["instance_name"],
            service_account_name=expected_values["service_account_name"],
            gpu_accelerator_type="NVIDIA_TESLA_T4",
            dataset_identifier=expected_values["dataset_identifier"],
            user_email=expected_values["user_email"],
            bucket_name=expected_values["bucket_name"],
            vm_image="img-1",
            sharing_bucket_permission_dict=sharing_dict,
            user_permissions_list=permissions_list,
            collaborative="true",
            associated_event=expected_values["associated_event"],
        )

        # Assert
        subs = build.substitutions
        _assert_common_substitutions(subs, expected_values)
        _assert_jupyter_like_substitutions(
            subs, "NVIDIA_TESLA_T4", "img-1", sharing_dict, permissions_list, "true"
        )
        assert subs["_WORKBENCH_TYPE"] == WorkbenchType.COLLABORATIVE
        _assert_build_configuration(build)

    def test_create_rstudio_workbench_build_substitutions(self, common_config_setup):
        """Verify RStudio build, including SSL certificate fetching logic."""
        # Arrange
        mock_config = common_config_setup
        mock_config.rstudio_certificate_secret_id = "secret-id"
        mock_config.rstudio_image_url = "gcr.io/img"
        mock_config.rstudio_startup_script = "gs://script"
        mock_config.network_name = "default"
        mock_config.rstudio_dns_project = "dns-proj"
        mock_config.rstudio_dns_zone = "dns-zone"
        mock_config.rstudio_domain_name = "example.com"

        # Mock Secret Manager response
        mock_secret_payload = MagicMock()
        mock_secret_payload.payload.data.decode.return_value = json.dumps(
            {
                "tls_key": "fake-key",
                "tls_crt": "fake-crt",
                "expiration_date": "2025-01-01",
            }
        )
        mock_config.google_secret_manager_client.access_secret_version.return_value = (
            mock_secret_payload
        )

        expected_values = {
            **COMMON_EXPECTED_VALUES,
            "instance_name": "rs-1",
            "service_account_name": "sa-1",
            "associated_event": "test-event-456",
        }

        sharing_dict = {"shared-bucket": "read_write"}
        permissions_list = ["roles/viewer", "roles/editor"]

        # Act
        build = builds.create_rstudio_workbench_build(
            workspace_project_id=expected_values["workspace_project_id"],
            workspace_numeric_id="12345",
            region=expected_values["region"],
            zone=expected_values["zone"],
            machine_type=expected_values["machine_type"],
            disk_size=expected_values["disk_size"],
            instance_name=expected_values["instance_name"],
            service_account_name=expected_values["service_account_name"],
            gpu_accelerator_type=None,
            dataset_identifier=expected_values["dataset_identifier"],
            user_email=expected_values["user_email"],
            bucket_name=expected_values["bucket_name"],
            sharing_bucket_permission_dict=sharing_dict,
            user_permissions_list=permissions_list,
            associated_event=expected_values["associated_event"],
        )

        # Assert
        subs = build.substitutions
        _assert_common_substitutions(
            subs, expected_values, include_organization_id=False
        )

        # RStudio-specific assertions
        assert (
            subs["_GPU_ACCELERATOR"] == ""
        )  # None should be normalized to empty string
        assert subs["_VM_IMAGE"] == "gcr.io/img"
        assert subs["_BRAND_NAME"] == "projects/12345/brands/12345"
        assert subs["_RSTUDIO_STARTUP_SCRIPT_BUCKET"] == "gs://script"
        assert subs["_NETWORK_NAME"] == "default"
        assert subs["_RSTUDIO_DNS_PROJECT"] == "dns-proj"
        assert subs["_RSTUDIO_DNS_ZONE"] == "dns-zone"
        assert subs["_RSTUDIO_DOMAIN_NAME"] == "example.com"
        assert subs["_RSTUDIO_SSL_PRIVATE_KEY"] == "fake-key"
        # The full certificate chain exceeds the 4000-char Cloud Build
        # substitution limit, so it is delivered via Secret Manager
        # (available_secrets -> RSTUDIO_CERTIFICATE_SECRET env) rather than as a
        # substitution. Asserted below via available_secrets.
        assert "_RSTUDIO_SSL_CERTIFICATE" not in subs
        assert subs["_RSTUDIO_SSL_EXPIRATION_DATE"] == "2025-01-01"
        assert subs["_WORKBENCH_TYPE"] == WorkbenchType.RSTUDIO
        assert subs["_SHARING_BUCKET_IDENTIFIERS"] == ",".join(sharing_dict.keys())
        assert subs["_SHARING_BUCKET_PERMISSIONS"] == ",".join(sharing_dict.values())
        assert subs["_USER_PERMISSIONS_LIST"] == ",".join(permissions_list)

        # Verify Secret Manager was called correctly
        mock_config.google_secret_manager_client.access_secret_version.assert_called_with(
            request={"name": "secret-id"}
        )

        # The certificate chain is exposed to the build as a secret env, not a
        # substitution.
        secret_envs = {
            s.env: s.version_name for s in build.available_secrets.secret_manager
        }
        assert secret_envs.get("RSTUDIO_CERTIFICATE_SECRET") == "secret-id"

        _assert_build_configuration(build)
