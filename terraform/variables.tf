variable "project_id" {
  type = string
}

variable "region" {
  default = "us-central1"
  type    = string
}

locals {
  cloud_run_services_without_defaults = [
    {
      service_name         = "identity-provisioning",
      service_account_name = "user-creator@workspace-controller-dev.iam.gserviceaccount.com"
      image                = "gcr.io/workspace-controller-dev/cloud_identity_cr_add_users@sha256:a09b9d3bed700df904f9941c73324ba7c7ec7ddd3c68b1082756ecd2069282f2"
    }
  ]

  cloud_run_defaults = {
    service_account_name = "workspace-creator@workspace-controller-dev.iam.gserviceaccount.com"
    min_scale            = "1"
    max_scale            = "100"
  }

  cloud_run_services = [
    for service_config in local.cloud_run_services_without_defaults :
    merge(local.cloud_run_defaults, service_config)
  ]
}
