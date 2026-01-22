terraform {
  required_version = ">= 1.5.0"
  required_providers {
    render = {
      source  = "render-oss/render"
      version = "~> 1.5"
    }
  }
}

provider "render" {
  owner_id = var.render_owner_id
  api_key = var.render_api_key
}

resource "render_web_service" "smart_chat_bot" {
  name           = var.service_name
  region         = var.region
  plan           = "starter"
  start_command  = "uv run python main.py"

  runtime_source = {
    native_runtime = {
      runtime       = "python"
      repo_url      = var.repo_url
      branch        = var.branch
      build_command = "uv sync"
      auto_deploy   = true
    }
  }

  env_vars = {
    PORT = {
      value = "8000"
    }
    SMART_CHAT_BOT_PORT = {
      value = "8000"
    }
    SMART_CHAT_BOT_HOST = {
      value = "0.0.0.0"
    }
    DISCORD_BOT_TOKEN = {
      value = var.discord_bot_token
    }
    GMAIL_CREDENTIALS_PATH = {
      value = "/etc/secrets/credentials.json"
    }
    GMAIL_REDIRECT_URI = {
      value = "https://smartchatbot-1ago.onrender.com/auth/mail/callback"
    }
    GMAIL_TOKEN_DB_PATH = {
      value = ""
    }
    ANTHROPIC_API_KEY = {
      value = var.anthropic_api_key
    }
  }
}
