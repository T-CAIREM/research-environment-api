provider "kubernetes" {
  host                   = "https://${module.gke.endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(module.gke.ca_certificate)
}

data "google_service_account" "modules-service-account" {
  account_id = "projects/${var.project_id}/serviceAccounts/${var.service_account_name}"
}

resource "google_dns_record_set" "kube-dns-a" {
  name         = "kube.api.dev.healthdatanexus.ai."
  type         = "A"
  ttl          = 300
  managed_zone = "api-dev-healthdatanexus-ai"
  rrdatas      = [google_compute_global_address.lb-ip.address]
}

resource "google_service_account" "backend-service-account" {
  account_id   = "${var.name}-pods"
  display_name = "Terraform-managed service account for ${var.name}-cluster backend pods"
}

resource "google_project_iam_member" "backend-service-account_storage-admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.backend-service-account.email}"
}

resource "google_service_account" "cloud-sql-service-account" {
  account_id   = "${var.name}-sql"
  display_name = "Terraform-managed service account for connecting to cloud-sql databases"
}

resource "google_project_iam_member" "cloud-sql-service-account_cloudsql-client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud-sql-service-account.email}"
}

resource "google_service_account_iam_binding" "cloud-sql-service-account" {
  service_account_id = google_service_account.cloud-sql-service-account.id
  role               = "roles/iam.workloadIdentityUser"
  members            = ["serviceAccount:${var.project_id}.svc.id.goog[default/${var.name}-cloud-sql]"]
}



resource "google_service_account_iam_binding" "backend-service-account" {
  service_account_id = data.google_service_account.modules-service-account.id
  role               = "roles/iam.workloadIdentityUser"
  members            = ["serviceAccount:${var.project_id}.svc.id.goog[default/${var.name}-backend]"]
}

resource "kubernetes_service_account" "cloud-sql" {
  metadata {
    name = "${var.name}-cloud-sql"

    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.cloud-sql-service-account.email
    }
  }
}

resource "kubernetes_service_account" "backend" {
  metadata {
    name = "${var.name}-backend"

    annotations = {
      "iam.gke.io/gcp-service-account" = var.service_account_name
    }
  }
}


resource "kubernetes_secret" "cloud-sql-service-account-token" {
  metadata {
    name = "${var.name}-cloud-sql-service-account-token"
    annotations = {
      "kubernetes.io/service-account.name" = kubernetes_service_account.cloud-sql.metadata[0].name
    }
  }
  type = "kubernetes.io/service-account-token"

  depends_on = [kubernetes_service_account.cloud-sql]
}

resource "google_service_account_key" "backend-service-key" {
  service_account_id = data.google_service_account.modules-service-account.name
}

# Forces the backend-service-key secret to be recreated after key change
resource "random_id" "backend-service-key" {
  byte_length = 8
  keepers = {
    private-key = google_service_account_key.backend-service-key.private_key
  }
}

resource "kubernetes_secret" "backend-service-key" {
  metadata {
    name = "backend-service-key-${random_id.backend-service-key.hex}"
  }
  data = {
    "credentials.json" = base64decode(google_service_account_key.backend-service-key.private_key)
  }
}


variable "_backend_volumes" {
  default = {
  }
}

locals {
  common_env = {
    APP_ENV                             = "production"
    PORT                                = 5000
    C_FORCE_ROOT                        = "True"
    SERVICE_ACCOUNT_CREDENTIALS_PATH    = "/var/secrets/google/credentials.json"
    CLOUD_BUILD_SERVICE_ACCOUNT_NAME    = var.cloud_build_service_account_name
    PROJECT_ID                          = var.project_id
    DATABASE_NAME                       = var.database_name
    DATABASE_USER                       = var.service_account_name
    CLOUD_SQL_INSTANCE_CONNECTION_NAME  = var.cloud_sql_instance_connection_name
    CELERY_RESULT_BACKEND               = "redis://${google_redis_instance.redis.host}:${google_redis_instance.redis.port}"
    CELERY_BROKER_URL                   = "redis://${google_redis_instance.redis.host}:${google_redis_instance.redis.port}"
    CACHE_TYPE                          = var.cache_type
    BILLING_ACCOUNT_CREATOR_GROUP_ID    = var.billing_account_creator_group_id
    VPC_SECURE_PERIMETER_NAME           = var.vpc_secure_perimeter_name
    TERRAFORM_REPO_NAME                 = var.terraform_repo_name
    TERRAFORM_BRANCH_NAME               = var.terraform_branch_name
    JUPYTER_STARTUP_SCRIPT              = var.jupyter_startup_script
    RSTUDIO_IMAGE_URL                   = var.rstudio_image_url
    DATA_PROJECT_NAME                   = var.data_project_name
    RSTUDIO_STARTUP_SCRIPT              = var.rstudio_startup_script
    NETWORK_NAME                        = var.network_name
    RSTUDIO_DNS_PROJECT                 = var.rstudio_dns_project
    RSTUDIO_DNS_ZONE                    = var.rstudio_dns_zone
    RSTUDIO_DOMAIN_NAME                 = var.rstudio_domain_name
    RSTUDIO_SSL_PRIVATE_KEY             = var.rstudio_ssl_private_key
    RSTUDIO_SSL_CERTIFICATE             = var.rstudio_ssl_certificate
    SHARING_FOLDER_ID                   = var.sharing_folder_id
    WORKBENCHES_PARENT_PROJECT_ID       = var.workbenches_parent_project_id
    GCP_SIGNED_URL_EXPIRATION_TIME      = var.gcp_signed_url_expiration_time
    GCP_CORS_ALLOWED_ORIGINS            = var.gcp_cors_allowed_origins
    ORGANIZATION_ID                     = var.cloud_organization_id
    CLOUD_RESEARCH_ENVIRONMENTS_API_URL = var.cloud_research_environments_api_url
    CUSTOMER_ID                         = var.gcp_customer_id
    GITHUB_SSH_KEY_KSM_ID               = var.github_ssh_key_ksm_id
    MONITORING_CSV_EXPORTS_ROOT_BUCKET  = var.monitoring_csv_exports_root_bucket
  }

  _backend_volumes = {
    "backend-service-key" = {
      include     = true
      secret_name = kubernetes_secret.backend-service-key.metadata[0].name
      mount_path  = "/var/secrets/google"
    },
  }

  backend_volumes = { for k, v in local._backend_volumes : k => v if v.include }
}


resource "kubernetes_deployment" "core" {
  metadata {
    name = "${var.name}-core"
    labels = {
      App = "${var.name}-core"
    }
  }

  spec {
    replicas = var.backend_replicas
    selector {
      match_labels = {
        App = "${var.name}-core"
      }
    }
    strategy {
      type = "RollingUpdate"
      rolling_update {
        max_surge       = 0
        max_unavailable = "50%"
      }
    }
    template {
      metadata {
        labels = {
          App = "${var.name}-core"
        }
      }
      spec {
        service_account_name = "${var.name}-backend"

        dynamic "volume" {
          for_each = local.backend_volumes

          content {
            name = volume.key
            secret {
              secret_name = volume.value.secret_name
            }
          }
        }

        container {
          name    = "core"
          image   = "${var.image_repository}:${var.image_tag}"
          command = null

          resources {
            limits = {
              cpu    = "500m"
              memory = "2Gi"
            }
          }

          dynamic "volume_mount" {
            for_each = local.backend_volumes

            content {
              name       = volume_mount.key
              mount_path = volume_mount.value.mount_path
              read_only  = true
            }
          }

          dynamic "env" {
            for_each = local.common_env

            content {
              name  = env.key
              value = env.value
            }
          }

          readiness_probe {
            http_get {
              port = 5000
              path = "/"
            }
          }

          liveness_probe {
            tcp_socket {
              port = 5000
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_deployment" "celery" {
  metadata {
    name = "${var.name}-celery"
    labels = {
      App = "${var.name}-celery"
    }
  }

  spec {
    replicas = var.backend_replicas
    selector {
      match_labels = {
        App = "${var.name}-celery"
      }
    }
    strategy {
      type = "RollingUpdate"
      rolling_update {
        max_surge       = 0
        max_unavailable = "50%"
      }
    }
    template {
      metadata {
        labels = {
          App = "${var.name}-celery"
        }
      }
      spec {
        service_account_name = "${var.name}-backend"

        dynamic "volume" {
          for_each = local.backend_volumes

          content {
            name = volume.key
            secret {
              secret_name = volume.value.secret_name
            }
          }
        }

        container {
          name    = "celery"
          image   = "${var.image_repository}:${var.image_tag}"
          command = ["/celery_endpoint.sh"]

          resources {
            limits = {
              cpu    = "500m"
              memory = "2Gi"
            }
          }

          dynamic "volume_mount" {
            for_each = local.backend_volumes

            content {
              name       = volume_mount.key
              mount_path = volume_mount.value.mount_path
              read_only  = true
            }
          }

          dynamic "env" {
            for_each = local.common_env

            content {
              name  = env.key
              value = env.value
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_deployment" "celery-flower" {
  metadata {
    name = "${var.name}-celery-flower"
    labels = {
      App = "${var.name}-celery-flower"
    }
  }

  spec {
    replicas = 1
    selector {
      match_labels = {
        App = "${var.name}-celery-flower"
      }
    }
    strategy {
      type = "RollingUpdate"
      rolling_update {
        max_surge       = 0
        max_unavailable = "50%"
      }
    }
    template {
      metadata {
        labels = {
          App = "${var.name}-celery-flower"
        }
      }
      spec {
        service_account_name = "${var.name}-backend"

        dynamic "volume" {
          for_each = local.backend_volumes

          content {
            name = volume.key
            secret {
              secret_name = volume.value.secret_name
            }
          }
        }

        container {
          name    = "celery-flower"
          image   = "${var.image_repository}:${var.image_tag}"
          command = ["/flower_endpoint.sh"]

          resources {
            limits = {
              cpu    = "200m"
              memory = "1Gi"
            }
          }

          dynamic "volume_mount" {
            for_each = local.backend_volumes

            content {
              name       = volume_mount.key
              mount_path = volume_mount.value.mount_path
              read_only  = true
            }
          }

          dynamic "env" {
            for_each = local.common_env

            content {
              name  = env.key
              value = env.value
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_horizontal_pod_autoscaler_v2" "backend_hpa" {
  metadata {
    name = "${var.name}-backend-hpa"
  }

  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = "${var.name}-core"
    }

    min_replicas = var.backend_replicas
    max_replicas = var.backend_replicas_max

    behavior {
      scale_down {
        # observe for 5 minutes
        stabilization_window_seconds = 300
        select_policy                = "Min"
        policy {
          # scale down one pod every 30 seconds if conditions met
          period_seconds = 30
          type           = "Pods"
          value          = 1
        }
      }

      scale_up {
        # observe for 15 seconds
        stabilization_window_seconds = 15
        select_policy                = "Max"
        policy {
          # scale up one pod every 15 seconds if conditions met
          period_seconds = 15
          type           = "Pods"
          value          = var.scale_up_step
        }
      }
    }

    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = 60
        }
      }
    }
  }
}

resource "kubernetes_deployment" "cloud-sql" {
  metadata {
    name = "${var.name}-cloud-sql"
    labels = {
      App = "${var.name}-cloud-sql"
    }
  }

  spec {
    replicas = 1
    selector {
      match_labels = {
        App = "${var.name}-cloud-sql"
      }
    }
    template {
      metadata {
        labels = {
          App = "${var.name}-cloud-sql"
        }
      }
      spec {
        service_account_name = "${var.name}-cloud-sql"

        container {
          name  = "cloud-sql-proxy"
          image = "gcr.io/cloudsql-docker/gce-proxy:${var.cloud_sql_proxy_tag}"

          command = [
            "/cloud_sql_proxy",
            "-verbose=false",
            "-structured_logs",
            "-instances=${var.project_id}:${var.region}:${google_sql_database_instance.main.name}=tcp:0.0.0.0:5432"
          ]

          resources {
            requests = {
              cpu    = "50m"
              memory = "8Mi"
            }
            limits = {
              cpu    = "75m"
              memory = "16Mi"
            }
          }

          security_context {
            run_as_non_root = true
          }
        }
      }
    }
  }
}

resource "kubernetes_cron_job_v1" "migrate" {

  metadata {
    name = "migrate"
  }

  spec {
    concurrency_policy            = "Replace"
    failed_jobs_history_limit     = 3
    schedule                      = "0 0 31 2 *"
    successful_jobs_history_limit = 1
    suspend                       = true
    job_template {
      metadata {}
      spec {
        backoff_limit              = 2
        ttl_seconds_after_finished = 10
        template {
          metadata {}
          spec {
            service_account_name = "${var.name}-backend"

            dynamic "volume" {
              for_each = local.backend_volumes

              content {
                name = volume.key
                secret {
                  secret_name = volume.value.secret_name
                }
              }
            }

            container {
              name    = "research-environment-api-dev-app"
              image   = "${var.image_repository}:${var.image_tag}"
              command = ["/bin/sh"]
              args    = ["-c", "alembic upgrade head"]

              dynamic "volume_mount" {
                for_each = local.backend_volumes

                content {
                  name       = volume_mount.key
                  mount_path = volume_mount.value.mount_path
                  read_only  = true
                }
              }

              dynamic "env" {
                for_each = local.common_env

                content {
                  name  = env.key
                  value = env.value
                }
              }
            }
            restart_policy = "Never"
          }
        }
      }
    }
  }
}


resource "kubernetes_service" "core" {
  metadata {
    name = "${var.name}-core"
    annotations = {
      "cloud.google.com/backend-config" = "{\"default\": \"${kubernetes_manifest.lb-backend.manifest.metadata.name}\"}"
    }
  }
  spec {
    type = "NodePort"
    selector = {
      App = kubernetes_deployment.core.spec.0.template.0.metadata[0].labels.App
    }
    port {
      name        = "http"
      protocol    = "TCP"
      port        = 5000
      target_port = 5000
    }
  }
}

resource "kubernetes_service" "cloud-sql" {
  metadata {
    name = "${var.name}-cloud-sql"
  }
  spec {
    selector = {
      App = kubernetes_deployment.cloud-sql.spec.0.template.0.metadata[0].labels.App
    }
    port {
      name     = "postgres"
      protocol = "TCP"
      port     = 5432
    }
  }
  lifecycle {
    # Annotations store information about Network Endpoint Groups managed by GCP
    ignore_changes = [metadata[0].annotations]
  }
}

resource "google_compute_global_address" "lb-ip" {
  name = "${var.name}-lb-ip"
}

resource "kubernetes_manifest" "lb-cert" {
  manifest = {
    "apiVersion" = "networking.gke.io/v1"
    "kind"       = "ManagedCertificate"
    "metadata" = {
      "name"      = "${var.name}-cert"
      "namespace" = "default"
    }
    "spec" = {
      "domains" = [var.domain]
    }
  }
}

resource "kubernetes_manifest" "lb-frontend" {
  manifest = {
    "apiVersion" = "networking.gke.io/v1beta1"
    "kind"       = "FrontendConfig"
    "metadata" = {
      "name"      = "${var.name}-lb-frontend"
      "namespace" = "default"
    }
    "spec" = {
      "redirectToHttps" = {
        "enabled" = false
      }
    }
  }
}

resource "kubernetes_manifest" "lb-backend" {
  manifest = {
    "apiVersion" = "cloud.google.com/v1"
    "kind"       = "BackendConfig"
    "metadata" = {
      "name"      = "${var.name}-lb-backend"
      "namespace" = "default"
    }
    "spec" = {
      "timeoutSec" = 300
    }
  }
}

resource "kubernetes_ingress_v1" "core" {
  metadata {
    name = "${var.name}-backend"
    annotations = {
      "kubernetes.io/ingress.class"                 = "gce"
      "kubernetes.io/ingress.global-static-ip-name" = google_compute_global_address.lb-ip.name
      "networking.gke.io/managed-certificates"      = kubernetes_manifest.lb-cert.manifest.metadata.name
      "networking.gke.io/v1beta1.FrontendConfig"    = kubernetes_manifest.lb-frontend.manifest.metadata.name
    }
  }
  spec {
    rule {
      http {
        path {
          backend {
            service {
              name = kubernetes_service.core.metadata[0].name
              port {
                number = kubernetes_service.core.spec[0].port[0].port
              }
            }
          }

          path = "/*"
        }
      }
    }
  }
}
