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

variable "image_repository" {
  type = string
}

variable "image_tag" {
  type = string
}

variable "database_name" {
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

variable "db_password_secret_name" {
  type = string
}

variable "billing_account_creator_group_id" {
  type = string
}

variable "legacy_cloud_research_environments_api_url" {
  type = string
}

variable "legacy_cloud_research_environments_gateway_audience" {
  type = string
}

variable "legacy_cloud_research_environments_credentials_secret_name" {
  type = string
}

variable "service_account_credentials_secret_name" {
  type = string
}

variable "celery_broker_url" {
  type = string
}

variable "celery_backend_url" {
  type = string
}
