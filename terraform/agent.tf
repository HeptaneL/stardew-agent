resource "docker_image" "agent" {
  name         = "stardew-agent:latest"
  keep_locally = true

  build {
    context    = abspath("${path.module}/..")
    dockerfile = "Dockerfile"
    tag        = ["stardew-agent:latest"]
  }
}

resource "docker_container" "agent" {
  name    = "stardew-agent"
  image   = docker_image.agent.image_id
  restart = "unless-stopped"

  networks_advanced {
    name    = docker_network.stardew.name
    aliases = ["agent"]
  }

  ports {
    internal = 8000
    external = var.agent_port
  }

  env = [
    "MODEL=${var.model}",
    "BASE_URL=${var.base_url}",
    "OPENAI_API_KEY=${var.openai_api_key}",
    "STARDEW_MCP_TRANSPORT=${var.stardew_mcp_transport}",
    "STARDEW_MCP_URL=http://mcp:8001/mcp",
    "DATABASE_URL=postgresql://${var.postgres_user}:${var.postgres_password}@postgres:5432/${var.postgres_db}",
    "NO_PROXY=localhost,127.0.0.1,::1,mcp,postgres",
    "no_proxy=localhost,127.0.0.1,::1,mcp,postgres",
  ]

  # Kept for parity with the MCP container. The agent itself only needs it if
  # STARDEW_MCP_TRANSPORT is later switched back to stdio inside the container.
  host {
    host = "host.docker.internal"
    ip   = "host-gateway"
  }

  healthcheck {
    test         = ["CMD", "python", "-c", "import socket; socket.create_connection(('127.0.0.1', 8000), 2)"]
    interval     = "5s"
    timeout      = "3s"
    retries      = 10
    start_period = "15s"
  }

  wait         = true
  wait_timeout = 120

  depends_on = [docker_container.postgres, docker_container.mcp]
}
