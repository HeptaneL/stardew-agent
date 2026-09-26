resource "docker_volume" "postgres_data" {
  name = "stardew-postgres-data"
}

resource "docker_image" "postgres" {
  name         = "postgres:16-alpine"
  keep_locally = true
}

resource "docker_container" "postgres" {
  name    = "stardew-postgres"
  image   = docker_image.postgres.image_id
  restart = "unless-stopped"

  networks_advanced {
    name    = docker_network.stardew.name
    aliases = ["postgres"]
  }

  ports {
    internal = 5432
    external = var.postgres_port
  }

  env = [
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "POSTGRES_DB=${var.postgres_db}",
  ]

  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
  }

  healthcheck {
    test         = ["CMD-SHELL", "pg_isready -U ${var.postgres_user} -d ${var.postgres_db}"]
    interval     = "5s"
    timeout      = "3s"
    retries      = 10
    start_period = "10s"
  }

  wait = true
}
