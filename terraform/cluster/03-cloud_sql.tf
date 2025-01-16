resource "google_compute_global_address" "db-ip-range" {
  name          = "${var.name}-db-ip-range"
  network       = google_compute_network.gke-network.id
  address_type  = "INTERNAL"
  purpose       = "VPC_PEERING"
  address       = "10.1.0.0"
  prefix_length = 16
}

resource "google_sql_database_instance" "main" {
  name             = "${var.name}-${terraform.workspace}"
  region           = var.region
  database_version = "POSTGRES_15"
  root_password = "postgres"

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }

  deletion_protection = var.deletion_protection
}

resource "time_sleep" "wait_30_seconds" {
  depends_on = [google_sql_database_instance.main]

  create_duration = "30s"
}

resource "google_sql_database" "database" {
  name      = var.database_name
  instance  = google_sql_database_instance.main.name
  charset   = "UTF8"
  collation = "en_US.UTF8"

  depends_on = [
    time_sleep.wait_30_seconds
  ]
}


resource "google_sql_user" "user" {
  instance = google_sql_database_instance.main.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
  name     = replace(var.service_account_name, ".gserviceaccount.com", "")

  depends_on = [
    time_sleep.wait_30_seconds
  ]
}
