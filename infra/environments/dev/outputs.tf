output "raw_emails_bucket_name" {
  value = module.storage.raw_emails_bucket_name
}

output "agent_sessions_bucket_name" {
  value = module.storage.agent_sessions_bucket_name
}

output "alerts_topic_arn" {
  value = module.observability.alerts_topic_arn
}

output "billing_alerts_topic_arn" {
  value = module.observability.billing_alerts_topic_arn
}
