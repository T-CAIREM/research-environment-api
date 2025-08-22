provider "helm" {
  kubernetes = {
    host                   = "https://${data.google_container_cluster.cluster.endpoint}"
    token                  = data.google_client_config.default.access_token
    cluster_ca_certificate = base64decode(data.google_container_cluster.cluster.master_auth[0].cluster_ca_certificate)
  }
}

resource "helm_release" "cert_manager" {
  name             = "cert-manager"
  repository       = "https://charts.jetstack.io"
  chart            = "cert-manager"
  namespace        = "cert-manager"
  create_namespace = true
  version          = "v1.18.2"

  set = [
    {
      name  = "installCRDs"
      value = "true"
    }
  ]
}

resource "google_service_account" "cert-manager-dns-service-account" {
  account_id   = "cert-manager-dns-admin"
  display_name = "Service Account for Let's Encrypt DNS validation"
}

resource "google_project_iam_member" "service-account-dns-admin" {
  project = var.project_id
  role    = "roles/dns.admin"
  member  = "serviceAccount:${google_service_account.cert-manager-dns-service-account.email}"
}

resource "google_service_account_key" "cert_manager_dns_key" {
  service_account_id = google_service_account.cert-manager-dns-service-account.name
}

resource "kubernetes_secret" "cert_manager_dns_credentials" {
  metadata {
    name      = "${var.name}-cert-manager-credentials"
    namespace = "default"
  }
  data = {
    "credentials.json" = base64decode(google_service_account_key.cert_manager_dns_key.private_key)
  }
}

resource "kubernetes_manifest" "issuer" {
  depends_on = [helm_release.cert_manager]

  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "Issuer"
    metadata = {
      name      = "${var.name}-letsencrypt"
      namespace = "default"
    }
    spec = {
      acme = {
        email  = "monitoring@healthdatanexus.ai"
        server = "https://acme-v02.api.letsencrypt.org/directory"
        privateKeySecretRef = {
          name = "${var.name}-letsencrypt-account-key"
        }
        solvers = [
          {
            dns01 = {
              cloudDNS = {
                project = var.project_id
                serviceAccountSecretRef = {
                  name = "${var.name}-cert-manager-credentials"
                  key  = "credentials.json"
                }
              }
            }
          }
        ]
      }
    }
  }
}

resource "kubernetes_manifest" "certificate" {
  depends_on = [kubernetes_manifest.issuer]

  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "Certificate"
    metadata = {
      name      = "${var.name}-rstudio-certificate"
      namespace = "default"
    }
    spec = {
      secretName  = "${var.name}-rstudio-certificate"
      duration    = "2160h"
      renewBefore = "720h"
      dnsNames    = ["*.${var.rstudio_domain_name}"]
      issuerRef = {
        name = "${var.name}-letsencrypt"
        kind = "Issuer"
      }
    }
  }
}

resource "google_project_iam_member" "terraform_worker_secretmanager_admin" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:terraform-worker@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_service_account" "secret-sync-service-account" {
  account_id  = "cert-manager-secret-sync"
  description = "Service Account for syncing K8s secrets to Secret Manager"
}

resource "google_project_iam_member" "secret-sync-secretmanager-admin" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${google_service_account.secret-sync-service-account.email}"
}

resource "google_secret_manager_secret" "rstudio-certificate-secret" {
  depends_on = [google_project_iam_member.secret-sync-secretmanager-admin]
  secret_id = "${var.name}-rstudio-certificate"

  replication {
    auto {}
  }
}

resource "google_service_account_iam_binding" "secret-sync-workload-identity" {
  service_account_id = google_service_account.secret-sync-service-account.id
  role               = "roles/iam.workloadIdentityUser"
  members            = ["serviceAccount:${var.project_id}.svc.id.goog[default/${var.name}-secret-sync]"]
}

resource "kubernetes_service_account" "secret-sync" {
  metadata {
    name      = "${var.name}-secret-sync"
    namespace = "default"
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.secret-sync-service-account.email
    }
  }
}

resource "kubernetes_role" "secret_sync_role" {
  metadata {
    name      = "secret-sync-role"
    namespace = "default"
  }

  rule {
    api_groups = [""]
    resources  = ["secrets"]
    verbs      = ["get", "create", "update", "patch"]
  }
    rule {
        api_groups = ["cert-manager.io"]
        resources  = ["certificates"]
        verbs      = ["get"]
    }
}

resource "kubernetes_role_binding" "secret_sync_role_binding" {
  metadata {
    name      = "secret-sync-role-binding"
    namespace = "default"
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.secret_sync_role.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.secret-sync.metadata[0].name
    namespace = "default"
  }
}

resource "kubernetes_config_map" "secret-sync-script" {
  metadata {
    name      = "${var.name}-secret-sync-script"
    namespace = "default"
  }

  data = {
    "sync-script.sh" = file("${path.module}/sync-script.sh")
  }
}

resource "kubernetes_cron_job_v1" "secret-sync" {
  metadata {
    name      = "${var.name}-secret-sync"
    namespace = "default"
  }

  spec {
    schedule           = "0 12 * * *"
    concurrency_policy = "Replace"

    job_template {
      metadata {
        name = "${var.name}-cert-sync-job"
      }

      spec {
        template {
          metadata {
            name = "${var.name}-cert-sync-pod"
          }

          spec {
            service_account_name = kubernetes_service_account.secret-sync.metadata[0].name

            container {
              name  = "secret-sync"
              image = "google/cloud-sdk:slim"

              command = ["/bin/bash", "-c", "apt-get update && apt-get install -y kubectl jq && /scripts/sync-script.sh"]
              volume_mount {
                name       = "sync-script"
                mount_path = "/scripts"
              }
            }

            volume {
              name = "sync-script"
              config_map {
                name         = kubernetes_config_map.secret-sync-script.metadata[0].name
                default_mode = "0755"
              }
            }

            restart_policy = "OnFailure"
          }
        }
        backoff_limit              = 2
        ttl_seconds_after_finished = 86400
      }
    }
  }

  depends_on = [kubernetes_manifest.certificate]
}