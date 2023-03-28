variable "region" {
  type = string
}

variable "service_name" {
  type = string
}

variable "service_account_name" {
  type = string
}

variable "image" {
  type = string
}

variable "min_scale" {
  type    = string
  default = "1"
}

variable "max_scale" {
  type    = string
  default = "100"
}
