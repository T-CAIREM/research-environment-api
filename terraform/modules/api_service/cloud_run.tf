resource "google_cloud_run_service" "api_service" {
  name                       = var.service_name
  location                   = var.region
  autogenerate_revision_name = true

  template {
    spec {
      containers {
        image = var.image
        dynamic "env" {
          for_each = var.env
          content {
            name  = env.value.name
            value = env.value.value
          }
        }
      }
      service_account_name = var.service_account_name
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = var.min_scale
        "autoscaling.knative.dev/maxScale" = var.max_scale
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}
