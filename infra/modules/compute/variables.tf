variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "inventory_table_stream_arn" {
  type = string
}

variable "open_rfqs_table_name" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "agent_runtime_arn" {
  type = string
}

variable "lambda_source_dir" {
  type = string
}

variable "raw_emails_bucket_name" {
  type = string
}

variable "raw_emails_bucket_arn" {
  type = string
}

variable "inbound_email_queue_arn" {
  type = string
}

variable "idempotency_table_name" {
  type = string
}

variable "service_lambda_source_dir" {
  type = string
}

variable "log_retention_days" {
  type    = number
  default = 14
}
