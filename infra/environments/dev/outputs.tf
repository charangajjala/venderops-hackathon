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

output "ses_domain_verification_token" {
  value = module.messaging.ses_domain_verification_token
}

output "ses_dkim_tokens" {
  value = module.messaging.ses_dkim_tokens
}

output "inbound_email_queue_url" {
  value = module.messaging.inbound_email_queue_url
}

output "inbound_email_queue_arn" {
  value = module.messaging.inbound_email_queue_arn
}

output "inbound_email_dlq_url" {
  value = module.messaging.inbound_email_dlq_url
}
