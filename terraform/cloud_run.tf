resource "google_cloud_run_service" "api_service" {
  for_each = { for key, value in local.cloud_run_services : key => value }

  name                       = each.value.service_name
  location                   = var.region
  autogenerate_revision_name = true

  template {
    spec {
      containers {
        image = each.value.image
      }
      service_account_name = each.value.service_account_name
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = each.value.min_scale
        "autoscaling.knative.dev/maxScale" = each.value.max_scale
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}
