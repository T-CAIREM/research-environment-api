locals {
  legacy_cloud_research_environments_credentials_volume_name = "legacy_cloud_research_environments_credentials"
  service_account_credentials_volume_name                    = "service_account_credentials"
}

resource "google_cloud_run_service" "api" {
  name                       = "${var.name}-${terraform.workspace}-core"
  location                   = var.region
  autogenerate_revision_name = true

  template {
    spec {
      volumes {
        name = local.legacy_cloud_research_environments_credentials_volume_name
        secret {
          secret_name = var.legacy_cloud_research_environments_credentials_secret_name
        }
      }

      volumes {
        name = local.service_account_credentials_volume_name

        secret {
          secret_name = var.service_account_credentials_secret_name
        }
      }

      containers {
        image = "${var.image_repository}:${var.image_tag}"

        volume_mounts {
          name       = local.legacy_cloud_research_environments_credentials_volume_name
          mount_path = "/app/legacy_workspace_research_environments_secret"
        }

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
          name  = "CLOUD_RESEARCH_ENVIRONMENTS_API_URL"
          value = var.legacy_cloud_research_environments_api_url
        }

        env {
          name  = "GATEWAY_AUDIENCE"
          value = var.legacy_cloud_research_environments_gateway_audience
        }

        env {
          name  = "GATEWAY_SERVICE_ACCOUNT_CREDENTIALS_PATH"
          value = "/app/legacy_workspace_research_environments_secret/legacy-workspace-controller-credentials"
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
