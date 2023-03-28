provider "google" {
  credentials = file("./credentials.json")
  project     = var.project_id
}

terraform {
  backend "gcs" {
    credentials = "./credentials.json"
    bucket      = "healthdatanexus-research-environment-api-terraform-state"
  }
}
