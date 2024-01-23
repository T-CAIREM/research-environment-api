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

variable "celery_broker_url" {
  type = string
}

variable "celery_backend_url" {
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

variable "rstudio_dns_zone" {
  type = string
}

variable "rstudio_domain_name" {
  type = string
}

variable "network_name" {
  type = string
}

variable "rstudio_ssl_private_key" {
  type = string
}

variable "rstudio_ssl_certificate" {
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