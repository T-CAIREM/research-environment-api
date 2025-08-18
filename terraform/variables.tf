variable "name" {
  type    = string
  default = "research-environment-api"
}

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "service_account_name" {
  type = string
}

variable "cloud_build_service_account_name" {
  type = string
}

variable "image_repository" {
  type = string
}

variable "image_tag" {
  type = string
}

variable "database_name" {
  type = string
}

variable "cloud_sql_instance_connection_name" {
  type = string
}

variable "cache_type" {
  type = string
}

variable "terraform_repo_name" {
  type = string
}

variable "terraform_branch_name" {
  type = string
}

variable "vpc_secure_perimeter_name" {
  type = string
}

variable "jupyter_startup_script" {
  type = string
}

variable "min_scale" {
  type = number
}

variable "max_scale" {
  type = number
}

variable "db_tier" {
  type = string
}

variable "billing_account_creator_group_id" {
  type = string
}

variable "service_account_credentials_secret_name" {
  type = string
}

variable "rstudio_image_url" {
  type = string
}

variable "data_project_name" {
  type = string
}

variable "rstudio_startup_script" {
  type = string
}

variable "rstudio_dns_project" {
  type = string
}

variable "dns_zone" {
  type = string
}

variable "rstudio_domain_name" {
  type = string
}

variable "network_name" {
  type = string
}

variable "sharing_folder_id" {
  type = string
}

variable "workbenches_parent_project_id" {
  type = string
}

variable "gcp_signed_url_expiration_time" {
  type = string
}

variable "gcp_cors_allowed_origins" {
  type = string
}

variable "cloud_research_environments_api_url" {
  type = string
}

variable "cloud_organization_id" {
  type = string
}

variable "gcp_customer_id" {
  type = string
}

variable "github_ssh_key_ksm_id" {
  type = string
}

variable "gcs_project_id" {
  default = "data-project-333710"
  type    = string
}

variable "domain" {
  default = "kube.api.healthdatanexus.ai"
  type    = string
}

variable "zones" {
  default = ["us-central1-a"]
  type    = list(string)
}

variable "audit_bucket_retention_seconds" {
  default = 86400
  type    = number
}

variable "audit_bucket_retention_locked" {
  default = false
  type    = bool
}

variable "deletion_protection" {
  default = true
  type    = bool
}

variable "cloud_sql_proxy_tag" {
  default = "1.24.0"
  type    = string
}

variable "backend_replicas" {
  default = 1
  type    = number
}

variable "backend_replicas_max" {
  default = 5
  type    = number
}

variable "scale_up_step" {
  default = 1
  type    = number
}

variable "monitoring_csv_exports_root_bucket" {
  type = string
}

variable "flower_basic_auth" {
  type = string
  sensitive = true
}

variable "root_postgres_password" {
  default = "postgres"
  type = string
}

variable "rstudio_certificate_secret_id" {
  default = "projects/1094753623932/secrets/research-environment-api-rstudio-certificate/versions/latest"
  type    = string
}
