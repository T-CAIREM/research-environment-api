module "identity_provisioning" {
  source = "./modules/api_service"

  region               = var.region
  service_name         = "identity-provisioning"
  service_account_name = "identity-provisioner@workspace-controller-dev.iam.gserviceaccount.com"
  image                = "gcr.io/workspace-controller-dev/cloud_identity_cr_add_users@sha256:a09b9d3bed700df904f9941c73324ba7c7ec7ddd3c68b1082756ecd2069282f2"
  env = [
    { name: "PROJECT_ID", value: var.project_id },
    { name: "BILLING_ACCOUNT_CREATOR_GROUP_ID", value: var.billing_creator_group_id }
  ]
}

module "billing_management" {
  count  = 0 # TODO: Remove after finishing the billing management module
  source = "./modules/api_service"

  region               = var.region
  service_name         = "billing-management"
  service_account_name = "billing-manager@workspace-controller-dev.iam.gserviceaccount.com"
  image                = ""
  env = [
    { name: "PROJECT_ID", value: var.project_id }
  ]
}
