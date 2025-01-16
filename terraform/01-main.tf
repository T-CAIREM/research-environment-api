provider "google" {
  credentials = file("./credentials.json")
  project     = var.project_id
  region      = var.region
}

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.17"
    }
    null = {
      source = "hashicorp/null"
      version = "~> 3.0"
    }
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.16"
    }
  }

  backend "gcs" {
    credentials = "./credentials.json"
    bucket      = "research-environment-api-terraform-state"
  }
}

data "google_client_config" "default" {}
