output "postgres_url" {
  value     = "postgresql://${var.postgres_user}:${var.postgres_password}@localhost:${var.postgres_port}/${var.postgres_db}"
  sensitive = true
}

output "agent_chat_url" {
  value = "http://localhost:${var.agent_port}/chat"
}

output "mcp_endpoint" {
  value = "http://localhost:${var.mcp_port}/mcp"
}
