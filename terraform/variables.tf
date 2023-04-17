variable "name" {
  type    = string
  default = "research_environment_api"
}

variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "service_account_name" {
  type = string
}

variable "image_repository" {
  type    = string
  default = "default_repository"
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

variable "billing_creator_group_id" {
  type    = string
  default = "00xvir7l3d802t9"
}
