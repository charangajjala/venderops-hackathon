output "alerts_topic_arn" {
  description = "SNS topic ARN for general alerts (DLQ depth, Lambda errors, SES bounce rate, etc). Reuse this from other modules rather than creating a new topic."
  value       = aws_sns_topic.alerts.arn
}

output "billing_alerts_topic_arn" {
  description = "SNS topic ARN (us-east-1) the CloudWatch billing alarms notify."
  value       = aws_sns_topic.billing_alerts.arn
}
