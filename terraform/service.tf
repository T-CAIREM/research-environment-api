module "identity_provisioning" {
  source = "./modules/api_service"

  region               = var.region
  service_name         = "identity-provisioning"
  service_account_name = "user-creator@workspace-controller-dev.iam.gserviceaccount.com"
  image                = "gcr.io/workspace-controller-dev/cloud_identity_cr_add_users@sha256:a09b9d3bed700df904f9941c73324ba7c7ec7ddd3c68b1082756ecd2069282f2"
}
