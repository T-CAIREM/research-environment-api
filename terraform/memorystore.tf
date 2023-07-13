resource "google_redis_instance" "celery_backend" {
  name           = "${var.name}-${terraform.workspace}-celery"
  memory_size_gb = 1
}
