variable "postgres_user" {
  type        = string
  default     = "stardew"
  description = "Postgres user for the checkpoint database."
}

variable "postgres_password" {
  type        = string
  default     = "stardew"
  sensitive   = true
  description = "Postgres password for the checkpoint database."
}

variable "postgres_db" {
  type        = string
  default     = "stardew"
  description = "Postgres database name for checkpoints."
}

variable "postgres_port" {
  type        = number
  default     = 15432
  description = "Host port on which Postgres is published. Avoids clashing with a local Postgres on 5432; containers still talk to each other on the internal 5432."
}

variable "agent_port" {
  type        = number
  default     = 8000
  description = "Host port on which the stardew-agent FastAPI app is published."
}

variable "mcp_port" {
  type        = number
  default     = 8001
  description = "Host port on which the stardew MCP server is published."
}

variable "model" {
  type        = string
  default     = "deepseek-flash"
  description = "Model name passed to the agent's OpenAI-compatible client."
}

variable "base_url" {
  type        = string
  default     = "https://api.deepseek.com"
  description = "Base URL of the OpenAI-compatible API."
}

variable "openai_api_key" {
  type        = string
  default     = ""
  sensitive   = true
  description = "API key for the model provider. Set this in terraform.tfvars, not in code."
}

variable "stardew_api_url" {
  type        = string
  default     = "http://host.docker.internal:8788"
  description = "URL of the HelloStardew mod's HTTP bridge, reachable from the MCP container."
}

variable "stardew_mcp_transport" {
  type        = string
  default     = "streamable-http"
  description = "How the agent connects to the MCP server: stdio or streamable-http."

  validation {
    condition     = contains(["stdio", "http", "streamable-http"], var.stardew_mcp_transport)
    error_message = "stardew_mcp_transport must be one of: stdio, http, streamable-http."
  }
}
