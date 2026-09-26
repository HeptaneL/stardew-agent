resource "docker_image" "mcp" {
  name         = "stardew-mcp-server:latest"
  keep_locally = true

  build {
    context    = abspath("${path.module}/../../stardew-mcp-server")
    dockerfile = "Dockerfile"
    tag        = ["stardew-mcp-server:latest"]
  }
}

resource "docker_container" "mcp" {
  name    = "stardew-mcp-server"
  image   = docker_image.mcp.image_id
  restart = "unless-stopped"

  networks_advanced {
    name    = docker_network.stardew.name
    aliases = ["mcp"]
  }

  ports {
    internal = 8001
    external = var.mcp_port
  }

  env = [
    "MCP_TRANSPORT=streamable-http",
    "MCP_HOST=0.0.0.0",
    "MCP_PORT=8001",
    "MCP_HTTP_PATH=/mcp",
    "STARDEW_API_URL=${var.stardew_api_url}",
    "NO_PROXY=localhost,127.0.0.1,::1",
    "no_proxy=localhost,127.0.0.1,::1",
  ]

  # The mod runs on the host and listens on localhost. host.docker.internal
  # lets the MCP container reach it without falling back to the host network.
  host {
    host = "host.docker.internal"
    ip   = "host-gateway"
  }

  healthcheck {
    test         = ["CMD", "python", "-c", "import socket; socket.create_connection(('127.0.0.1', 8001), 2)"]
    interval     = "5s"
    timeout      = "3s"
    retries      = 10
    start_period = "10s"
  }

  wait = true
}
