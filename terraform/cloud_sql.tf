resource "google_sql_database_instance" "main" {
  name             = "${var.name}-${terraform.workspace}"
  region           = var.region
  database_version = "POSTGRES_15"

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }

  deletion_protection = true
}

resource "google_sql_user" "user" {
  instance = google_sql_database_instance.main.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
  name     = replace(var.service_account_name, ".gserviceaccount.com", "")
}
