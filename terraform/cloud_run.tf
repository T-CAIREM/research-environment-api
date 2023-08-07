locals {
  service_account_credentials_volume_name = "service_account_credentials"
  services = [
    { name = "core", command = null },
    { name = "celery", command = ["celery", "-A", "research_environment_api.celery_worker", "worker"] }
  ]
}

resource "google_cloud_run_service" "api" {
  for_each = {
    for index, service in local.services :
    service.name => service
  }

  name                       = "${var.name}-${terraform.workspace}-${each.value.name}"
  location                   = var.region
  autogenerate_revision_name = true

  template {
    spec {
      volumes {
        name = local.service_account_credentials_volume_name

        secret {
          secret_name = var.service_account_credentials_secret_name
        }
      }

      containers {
        image   = "${var.image_repository}:${var.image_tag}"
        command = each.value.command

        volume_mounts {
          name       = local.service_account_credentials_volume_name
          mount_path = "/app/core_service_account_secret"
        }
        env {
          name  = "APP_ENV"
          value = "production"
        }

        env {
          name  = "DATABASE_NAME"
          value = var.database_name
        }

        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "BILLING_ACCOUNT_CREATOR_GROUP_ID"
          value = var.billing_account_creator_group_id
        }

        env {
          name  = "SERVICE_ACCOUNT_CREDENTIALS_PATH"
          value = "/app/core_service_account_secret/core-service-account-key"
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
}
