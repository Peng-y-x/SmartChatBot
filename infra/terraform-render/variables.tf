variable "render_owner_id" {
  type = string
  description = "Render owner ID"
  default = ""
  sensitive = true
}

variable "render_api_key" {
  type        = string
  description = "Render API key"
  default     = ""
  sensitive   = true
}

variable "repo_url" {
  type        = string
  description = "Git repository URL (GitHub/GitLab)"
  default     = "REPLACE_ME"
}

variable "branch" {
  type        = string
  description = "Git branch to deploy"
  default     = "main"
}

variable "region" {
  type        = string
  description = "Render region"
  default     = "oregon"
}

variable "service_name" {
  type        = string
  description = "Render service name"
  default     = "smart-chat-bot"
}

variable "discord_bot_token" {
  type        = string
  description = "Discord bot token"
  sensitive   = true
  default     = ""
}

variable "anthropic_api_key" {
  type        = string
  description = "Anthropic API key (optional)"
  sensitive   = true
  default     = ""
}

