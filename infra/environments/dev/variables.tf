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
  description = "Domain SES receives mail for. pixelbuffer.club (not pixelbuffer.com - that domain is on EasyDNS with unrelated live mail/hosting we don't control). pixelbuffer.club is registered at Spaceship and delegated to Cloudflare, has no existing email setup, so the bare domain is used directly."
  type        = string
  default     = "pixelbuffer.club"
}

variable "receipt_rule_recipients" {
  description = "Addresses or domains the SES receipt rule matches."
  type        = list(string)
  default     = ["pixelbuffer.club"]
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for pixelbuffer.club, used to create the SES verification/DKIM/MX DNS records there."
  type        = string
}

variable "vendors" {
  description = "Vendor identifiers, each gets its own VendorStock DynamoDB table."
  type        = list(string)
  default     = ["cascade-packaging", "green-valley-dairy", "sunrise-farms"]
}
