resource "google_sql_database" "db" {
  name     = "${var.name}-${workspace.name}-db"
  instance = google_sql_database_instance.instance.name
}

resource "google_sql_database_instance" "instance" {
  name             = "${var.name}-${workspace.name}-instance"
  region           = var.region
  database_version = "POSTGRES_15"

  settings {
    tier = vars.db_tier
  }

  deletion_protection = true
}
