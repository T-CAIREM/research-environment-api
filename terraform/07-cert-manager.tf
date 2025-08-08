# is it okey with this new cert manager file? maybe remove helm ( manual installation of cert manager ) and keep everyting in kubernetes file?
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
        email  = "monitoring@healthdatanexus.ai" # email is required what should we pass here?
        server = "https://acme-staging-v02.api.letsencrypt.org/directory"
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
      duration    = "2160h" # it can be adjusted :) same with renewbefore
      renewBefore = "720h"
      dnsNames    = [var.rstudio_domain_name]
      issuerRef = {
        name = "${var.name}-letsencrypt"
        kind = "Issuer"
      }
    }
  }
}