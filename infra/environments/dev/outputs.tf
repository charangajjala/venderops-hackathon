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

output "inventory_table_name" {
  value = module.dynamodb.inventory_table_name
}

output "vendors_table_name" {
  value = module.dynamodb.vendors_table_name
}

output "vendor_stock_table_names" {
  value = module.dynamodb.vendor_stock_table_names
}

output "rfqs_table_name" {
  value = module.dynamodb.rfqs_table_name
}

output "open_rfqs_table_name" {
  value = module.dynamodb.open_rfqs_table_name
}

output "quotes_table_name" {
  value = module.dynamodb.quotes_table_name
}

output "purchase_orders_table_name" {
  value = module.dynamodb.purchase_orders_table_name
}

output "idempotency_table_name" {
  value = module.dynamodb.idempotency_table_name
}

output "agentcore_ecr_repository_url" {
  value = module.agentcore.ecr_repository_url
}

output "agentcore_agent_runtime_arn" {
  value = module.agentcore.agent_runtime_arn
}

output "agentcore_runtime_role_arn" {
  value = module.agentcore.runtime_role_arn
}

output "reorder_checker_function_name" {
  value = module.compute.reorder_checker_function_name
}

output "service_function_name" {
  value = module.compute.service_function_name
}
