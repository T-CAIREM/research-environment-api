variable "gke_machine_type" {
  default = "e2-medium"
  type    = string
}

resource "google_compute_network" "gke-network" {
  name                    = "${var.name}-network"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "gke-subnetwork" {
  name          = "${var.name}-subnetwork"
  region        = var.region
  network       = google_compute_network.gke-network.id
  ip_cidr_range = "10.0.1.0/24"

  secondary_ip_range {
    range_name    = "${var.name}-subnetwork-pods"
    ip_cidr_range = "172.16.0.0/18"
  }

  secondary_ip_range {
    range_name    = "${var.name}-subnetwork-services"
    ip_cidr_range = "172.16.64.0/20"
  }
}


module "gke" {
  source                     = "terraform-google-modules/kubernetes-engine/google"
  project_id                 = var.project_id
  name                       = "${var.name}-cluster"
  regional                   = false
  zones                      = var.zones
  network                    = google_compute_network.gke-network.name
  subnetwork                 = google_compute_subnetwork.gke-subnetwork.name
  ip_range_pods              = "${var.name}-subnetwork-pods"
  ip_range_services          = "${var.name}-subnetwork-services"
  http_load_balancing        = true
  horizontal_pod_autoscaling = true
  network_policy             = false
  default_max_pods_per_node  = 55
  remove_default_node_pool   = true
  kubernetes_version         = "latest"
  deletion_protection        = var.deletion_protection

  node_pools = [
    {
      name               = "default-node-pool"
      machine_type       = var.gke_machine_type
      e2machine_type     = var.gke_machine_type
      node_locations     = var.zones[0]
      min_count          = 1
      max_count          = 5
      local_ssd_count    = 0
      disk_size_gb       = 50
      disk_type          = "pd-standard"
      image_type         = "COS_CONTAINERD"
      auto_repair        = true
      auto_upgrade       = true
      service_account    = var.service_account_name
      preemptible        = false
      initial_node_count = 1
    },
  ]

  node_pools_oauth_scopes = {
    all = []

    default-node-pool = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
  }

  node_pools_labels = {
    all = {}

    default-node-pool = {
      default-node-pool = true
    }
  }

  node_pools_taints = {
    all = []

    default-node-pool = [
      {
        key    = "default-node-pool"
        value  = true
        effect = "PREFER_NO_SCHEDULE"
      },
    ]
  }

  node_pools_tags = {
    all = []

    default-node-pool = [
      "default-node-pool",
    ]
  }
}
