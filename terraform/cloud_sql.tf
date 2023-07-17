resource "google_sql_database_instance" "main" {
  name             = "${var.name}-${terraform.workspace}"
  region           = var.region
  database_version = "POSTGRES_15"

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"
  }

  deletion_protection = true
}

data "google_secret_manager_secret_version" "postgres_password" {
  secret = var.db_password_secret_name
}

resource "google_sql_user" "user" {
  name     = "dev"
  instance = google_sql_database_instance.main.name
  password = data.google_secret_manager_secret_version.postgres_password.secret_data
}
