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

variable "min_scale" {
  type = number
}

variable "max_scale" {
  type = number
}

variable "db_tier" {
  type = string
}
