locals {
  service_account_credentials_volume_name = "service_account_credentials"
  services = [
    { name = "core", command = null, cpu_throttling = true },
    { name = "celery", command = ["/celery_endpoint.sh"], cpu_throttling = false }
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

        # HACK: Use a different serializer. Pickle requires this to be set in order to work. Bad idea.
        env {
          name  = "C_FORCE_ROOT"
          value = "True"
        }

        env {
          name  = "APP_ENV"
          value = "production"
        }

        env {
          name  = "SERVICE_ACCOUNT_CREDENTIALS_PATH"
          value = "/app/core_service_account_secret/${var.service_account_credentials_secret_name}"
        }

        env {
          name  = "CLOUD_BUILD_SERVICE_ACCOUNT_NAME"
          value = var.cloud_build_service_account_name
        }

        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "DATABASE_NAME"
          value = var.database_name
        }

        env {
          name  = "DATABASE_USER"
          value = var.service_account_name
        }

        env {
          name  = "CLOUD_SQL_INSTANCE_CONNECTION_NAME"
          value = var.cloud_sql_instance_connection_name
        }

        env {
          name  = "CELERY_RESULT_BACKEND"
          value = var.celery_backend_url
        }

        env {
          name  = "CELERY_BROKER_URL"
          value = var.celery_broker_url
        }

        env {
          name  = "CACHE_TYPE"
          value = var.cache_type
        }

        env {
          name  = "BILLING_ACCOUNT_CREATOR_GROUP_ID"
          value = var.billing_account_creator_group_id
        }

        env {
          name  = "VPC_SECURE_PERIMETER_NAME"
          value = var.vpc_secure_perimeter_name
        }

        env {
          name  = "TERRAFORM_REPO_NAME"
          value = var.terraform_repo_name
        }

        env {
          name  = "TERRAFORM_BRANCH_NAME"
          value = var.terraform_branch_name
        }

        env {
          name  = "JUPYTER_STARTUP_SCRIPT"
          value = var.jupyter_startup_script
        }

        env {
          name  = "RSTUDIO_IMAGE_URL"
          value = var.rstudio_image_url
        }

        env {
          name  = "DATA_PROJECT_NAME"
          value = var.data_project_name
        }
      }

      service_account_name = var.service_account_name
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"        = var.min_scale
        "autoscaling.knative.dev/maxScale"        = var.max_scale
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.name
        "run.googleapis.com/cpu-throttling"       = each.value.cpu_throttling
      }
    }
  }
}
