locals {
  service_account_credentials_volume_name = "service_account_credentials"
  services = [
    { name = "core", command = null, cpu_throttling = true },
    { name = "celery", command = ["/celery_endpoint.sh"], cpu_throttling = false }
  ]

  env_vars = {
    APP_ENV = "production"
    C_FORCE_ROOT = "True"
    SERVICE_ACCOUNT_CREDENTIALS_PATH = "/app/core_service_account_secret/${var.service_account_credentials_secret_name}"
    CLOUD_BUILD_SERVICE_ACCOUNT_NAME = var.cloud_build_service_account_name
    PROJECT_ID = var.project_id
    DATABASE_NAME = var.database_name
    DATABASE_USER = var.service_account_name
    CLOUD_SQL_INSTANCE_CONNECTION_NAME = var.cloud_sql_instance_connection_name
    CELERY_RESULT_BACKEND = var.celery_backend_url
    CELERY_BROKER_URL = var.celery_broker_url
    CACHE_TYPE = var.cache_type
    BILLING_ACCOUNT_CREATOR_GROUP_ID = var.billing_account_creator_group_id
    VPC_SECURE_PERIMETER_NAME = var.vpc_secure_perimeter_name
    TERRAFORM_REPO_NAME = var.terraform_repo_name
    TERRAFORM_BRANCH_NAME = var.terraform_branch_name
    JUPYTER_STARTUP_SCRIPT = var.jupyter_startup_script
    RSTUDIO_IMAGE_URL = var.rstudio_image_url
    DATA_PROJECT_NAME = var.data_project_name
    RSTUDIO_STARTUP_SCRIPT = var.rstudio_startup_script
    NETWORK_NAME = var.network_name
    RSTUDIO_DNS_PROJECT = var.rstudio_dns_project
    RSTUDIO_DNS_ZONE = var.rstudio_dns_zone
    RSTUDIO_DOMAIN_NAME = var.rstudio_domain_name
    RSTUDIO_SSL_PRIVATE_KEY = var.rstudio_ssl_private_key
    RSTUDIO_SSL_CERTIFICATE = var.rstudio_ssl_certificate
    SHARING_FOLDER_ID = var.sharing_folder_id
    WORKBENCHES_PARENT_PROJECT_ID = var.workbenches_parent_project_id
    GCP_SIGNED_URL_EXPIRATION_TIME = var.gcp_signed_url_expiration_time
    GCP_CORS_ALLOWED_ORIGINS = var.gcp_cors_allowed_origins
    ORGANIZATION_ID = var.cloud_organization_id
    CLOUD_RESEARCH_ENVIRONMENTS_API_URL = var.cloud_research_environments_api_url
  }
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

        resources {
          limits = {
            memory = "3Gi"
          }
        }

        # HACK: Use a different serializer. Pickle requires this to be set in order to work. Bad idea.
        dynamic "env" {
          for_each = local.env_vars
          content {
            name  = env.key
            value = env.value
          }
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

resource "google_cloud_run_v2_job" "migrate" {
  name     = "migrate"
  location = "us-central1"

  template {
    template {
      volumes {
        name = local.service_account_credentials_volume_name

        secret {
          secret = var.service_account_credentials_secret_name
        }
      }

      containers {
        image   = "${var.image_repository}:${var.image_tag}"
        command = ["/bin/sh"]
        args = ["-c", "alembic upgrade head"]

        volume_mounts {
          name       = local.service_account_credentials_volume_name
          mount_path = "/app/core_service_account_secret"
        }

        dynamic "env" {
          for_each = local.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }
      }

      service_account = var.service_account_name
    }
  }
}
