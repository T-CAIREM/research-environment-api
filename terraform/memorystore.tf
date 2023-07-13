resource "google_redis_instance" "celery_backend" {
  name           = "${var.name}_${workspace.name}_celery_backend"
  memory_size_gb = 1
}
