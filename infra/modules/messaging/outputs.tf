output "ses_domain_verification_token" {
  value = aws_ses_domain_identity.this.verification_token
}

output "ses_dkim_tokens" {
  value = aws_ses_domain_dkim.this.dkim_tokens
}

output "inbound_email_topic_arn" {
  value = aws_sns_topic.inbound_email.arn
}

output "inbound_email_queue_arn" {
  value = aws_sqs_queue.inbound_email.arn
}

output "inbound_email_queue_url" {
  value = aws_sqs_queue.inbound_email.id
}

output "inbound_email_queue_name" {
  value = aws_sqs_queue.inbound_email.name
}

output "inbound_email_dlq_arn" {
  value = aws_sqs_queue.inbound_email_dlq.arn
}

output "inbound_email_dlq_url" {
  value = aws_sqs_queue.inbound_email_dlq.id
}

output "inbound_email_dlq_name" {
  value = aws_sqs_queue.inbound_email_dlq.name
}
