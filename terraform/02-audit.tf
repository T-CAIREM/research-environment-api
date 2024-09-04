resource "google_project_iam_audit_config" "gcs" {
  project = var.project_id
  service = "storage.googleapis.com"

  dynamic "audit_log_config" {
    for_each = ["ADMIN_READ", "DATA_READ", "DATA_WRITE"]

    content {
      log_type         = audit_log_config.value
      exempted_members = [google_logging_project_sink.audit.writer_identity]
    }
  }
}

resource "google_storage_bucket" "audit" {
  name                        = "${var.project_id}-${var.name}-audit"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = false

  retention_policy {
    retention_period = var.audit_bucket_retention_seconds
    is_locked        = var.audit_bucket_retention_locked
  }

  dynamic "lifecycle_rule" {
    for_each = {
      "COLDLINE" = 30,
      "ARCHIVE"  = 365,
    }

    content {
      condition {
        age = lifecycle_rule.value
      }
      action {
        type          = "SetStorageClass"
        storage_class = lifecycle_rule.key
      }
    }
  }
}

resource "google_logging_project_sink" "audit" {
  name                   = "Audit"
  destination            = "storage.googleapis.com/${google_storage_bucket.audit.name}"
  unique_writer_identity = true

  filter = "LOG_ID(\"cloudaudit.googleapis.com/data_access\")"
}

resource "google_storage_bucket_iam_member" "audit-log-writer" {
  bucket = google_storage_bucket.audit.name
  role   = "roles/storage.objectCreator"
  member = google_logging_project_sink.audit.writer_identity
}
