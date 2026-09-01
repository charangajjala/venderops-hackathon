output "raw_emails_bucket_name" {
  description = "Name of the S3 bucket SES writes raw inbound emails to."
  value       = aws_s3_bucket.raw_emails.id
}

output "raw_emails_bucket_arn" {
  value = aws_s3_bucket.raw_emails.arn
}

output "agent_sessions_bucket_name" {
  description = "Name of the S3 bucket AgentCore Runtime persists long-term session state to."
  value       = aws_s3_bucket.agent_sessions.id
}

output "agent_sessions_bucket_arn" {
  value = aws_s3_bucket.agent_sessions.arn
}
