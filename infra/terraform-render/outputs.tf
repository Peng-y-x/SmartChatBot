output "service_id" {
  description = "Render service ID"
  value       = render_web_service.smart_chat_bot.id
}

output "service_url" {
  description = "Render service URL"
  value       = render_web_service.smart_chat_bot.url
}
