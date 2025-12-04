import json
from unittest.mock import MagicMock

from research_environment_api.background import builds
from research_environment_api.modules.workbench_management.entities import (
    MachineType,
    Region,
    WorkbenchType,
)


class TestBuilds:
    def test_create_jupyter_workbench_build_substitutions(self, mock_config):
        """Verify that all Terraform variables are correctly populated."""
        # Arrange
        mock_config.cloud_build_service_account_name = (
            "projects/my-project/serviceAccounts/my-sa"
        )
        mock_config.github_ssh_key_ksm_id = (
            "projects/my-project/secrets/my-secret/versions/1"
        )
        mock_config.organization_id = "org-123"
        mock_config.terraform_repo_name = "tf-repo"
        mock_config.terraform_branch_name = "main"
        mock_config.jupyter_startup_script = "gs://script"

        # Act
        build = builds.create_jupyter_workbench_build(
            workspace_project_id="proj-1",
            region=Region.US_CENTRAL,
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
            collaborative="true",
        )

        # Assert
        # TODO: Expand assertions to cover all substitutions
        subs = build.substitutions
        assert subs["_PROJECT_ID"] == "proj-1"
        assert subs["_MACHINE_TYPE"] == "n1-standard-1"
        assert subs["_GPU_ACCELERATOR"] == "NVIDIA_TESLA_T4"
        assert subs["_WORKBENCH_TYPE"] == WorkbenchType.JUPYTER
        assert len(build.steps) > 0

    def test_create_rstudio_workbench_build_substitutions(self, mock_config):
        """Verify RStudio build, including SSL certificate fetching logic."""
        # Arrange:
        mock_config.cloud_build_service_account_name = (
            "projects/my-project/serviceAccounts/my-sa"
        )
        mock_config.github_ssh_key_ksm_id = (
            "projects/my-project/secrets/my-secret/versions/1"
        )
        mock_config.organization_id = "org-123"
        mock_config.rstudio_certificate_secret_id = "secret-id"
        mock_config.rstudio_image_url = "gcr.io/img"
        mock_config.rstudio_startup_script = "gs://script"
        mock_config.network_name = "default"
        mock_config.rstudio_dns_project = "dns-proj"
        mock_config.rstudio_dns_zone = "dns-zone"
        mock_config.rstudio_domain_name = "example.com"
        mock_config.terraform_repo_name = "tf-repo"
        mock_config.terraform_branch_name = "main"

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

        # Act
        build = builds.create_rstudio_workbench_build(
            workspace_project_id="proj-1",
            workspace_numeric_id="12345",
            region=Region.US_CENTRAL,
            zone="us-central1-a",
            machine_type=MachineType.N1_STANDARD_1,
            disk_size=100,
            instance_name="rs-1",
            service_account_name="sa-1",
            gpu_accelerator_type=None,
            dataset_identifier="ds-1",
            user_email="user@test.com",
            bucket_name="b-1",
            sharing_bucket_permission_dict={},
            user_permissions_list=[],
        )

        # Assert
        subs = build.substitutions
        assert subs["_WORKBENCH_TYPE"] == WorkbenchType.RSTUDIO
        assert subs["_RSTUDIO_SSL_PRIVATE_KEY"] == "fake-key"
        assert subs["_RSTUDIO_SSL_CERTIFICATE"] == "fake-crt"
        mock_config.google_secret_manager_client.access_secret_version.assert_called_with(
            request={"name": "secret-id"}
        )
