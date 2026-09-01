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

variable "ses_domain" {
  description = "Domain SES receives mail for."
  type        = string
  default     = "pixelbuffer.com"
}

variable "receipt_rule_recipients" {
  description = "Addresses or domains the SES receipt rule matches."
  type        = list(string)
  default     = ["pixelbuffer.com"]
}
