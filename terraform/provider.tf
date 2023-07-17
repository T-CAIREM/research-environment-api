provider "google" {
  credentials = file("./credentials.json")
  project     = var.project_id
  region      = var.region
}

terraform {
  backend "gcs" {
    credentials = "./credentials.json"
    bucket      = "research-environment-api-terraform-state"
  }
}
