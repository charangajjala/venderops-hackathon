variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "lambda_source_dir" {
  type = string
}

variable "inventory_table_name" {
  type = string
}

variable "vendors_table_name" {
  type = string
}

variable "rfqs_table_name" {
  type = string
}

variable "open_rfqs_table_name" {
  type = string
}

variable "quotes_table_name" {
  type = string
}

variable "purchase_orders_table_name" {
  type = string
}

variable "write_api_key" {
  description = "Shared secret the frontend sends as X-Api-Key on POST routes (approve/reject). HTTP APIs (apigatewayv2) don't support REST-API-style usage-plan API keys, so this is checked in-Lambda instead."
  type        = string
  sensitive   = true
}

variable "log_retention_days" {
  type    = number
  default = 14
}
