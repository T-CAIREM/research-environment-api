resource "google_sql_database" "db" {
  name     = "${var.name}-${terraform.workspace}-db"
  instance = google_sql_database_instance.instance.name
}

resource "google_sql_database_instance" "instance" {
  name             = "${var.name}-${terraform.workspace}-instance"
  region           = var.region
  database_version = "POSTGRES_15"

  settings {
    tier = var.db_tier
  }

  deletion_protection = true
}
