variable "project" {
  description = "Short project name used as a resource name prefix."
  type        = string
  default     = "vendorops"
}

variable "environment" {
  description = "Environment name."
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "Primary AWS region for this environment."
  type        = string
  default     = "us-east-1"
}

variable "alert_emails" {
  description = "Email addresses for billing and operational alerts. Each gets its own SNS subscription and its own confirmation email that must be clicked after apply."
  type        = list(string)
}

variable "monthly_budget_usd" {
  description = "Monthly AWS Budgets cost limit, in USD."
  type        = number
  default     = 45
}
