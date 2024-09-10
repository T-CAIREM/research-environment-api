resource "google_redis_instance" "redis" {
  name               = "${var.name}-${terraform.workspace}-redis"
  memory_size_gb     = 1
  authorized_network = "projects/research-environment-api-dev/global/networks/research-environment-api-network"
}
