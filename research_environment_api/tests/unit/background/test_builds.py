import pytest
from unittest.mock import MagicMock
from research_environment_api.background import builds
from research_environment_api.modules.workbench_management.entities import (
    MachineType, Region, WorkbenchType
)

class TestBuilds:
    """Test Cloud Build configuration generation."""

    def test_create_jupyter_workbench_build_substitutions(self, mock_config):
        """Verify that all Terraform variables are correctly populated."""
        # Arrange
        mock_config.organization_id = "org-123"
        mock_config.terraform_repo_name = "tf-repo"
        mock_config.terraform_branch_name = "main"
        mock_config.jupyter_startup_script = "gs://script"

        # Act
        build = builds.create_jupyter_workbench_build(
            workspace_project_id="proj-1",
            region=Region.US_CENTRAL1,
            zone="us-central1-a",
            machine_type=MachineType.N1_STANDARD_1,
            disk_size=100,
            instance_name="wb-1",
            service_account_name="sa-1",
            gpu_accelerator_type="NVIDIA_TESLA_T4",
            dataset_identifier="ds-1",
            user_email="user@test.com",
            bucket_name="b-1",
            vm_image="img-1",
            sharing_bucket_permission_dict={"shared-1": "READ"},
            user_permissions_list=["roles/viewer"],
            collaborative="true"
        )

        # Assert
        subs = build.substitutions
        assert subs["_PROJECT_ID"] == "proj-1"
        assert subs["_MACHINE_TYPE"] == "n1-standard-1"
        assert subs["_GPU_ACCELERATOR"] == "nvidia-tesla-t4"
        assert subs["_SHARING_BUCKET_IDENTIFIERS"] == "shared-1"
        assert subs["_ORGANIZATION_ID"] == "org-123"
        # Ensure correct template steps are loaded
        assert len(build.steps) > 0