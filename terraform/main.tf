terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 4.2.0"
    }
  }
}

locals {
  # Docker Desktop on macOS exposes its daemon at ~/.docker/run/docker.sock and
  # does not always create the provider's default /var/run/docker.sock. Default
  # to that socket, but allow "auto" to fall back to DOCKER_HOST / the provider
  # default, or an explicit socket URL (e.g. unix:///var/run/docker.sock).
  docker_host = var.docker_host == "" ? "unix://${pathexpand("~/.docker/run/docker.sock")}" : (
    var.docker_host == "auto" ? null : var.docker_host
  )
}

provider "docker" {
  host = local.docker_host
}

resource "docker_network" "stardew" {
  name = "stardew"
}
