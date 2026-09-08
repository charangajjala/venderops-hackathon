variable "project" {
  description = "Short project name used as a resource name prefix, e.g. \"vendorops\"."
  type        = string
}

variable "environment" {
  description = "Environment name, e.g. \"dev\" or \"prod\". Used as a resource name suffix."
  type        = string
}

variable "raw_email_retention_days" {
  description = "Days to keep raw inbound emails in the raw-emails bucket before expiring them. Controls storage cost - SES writes one object per inbound email, PDF attachments included."
  type        = number
  default     = 30
}

variable "ses_allowed_account_id" {
  description = "AWS account ID allowed to write to the raw-emails bucket via SES (the aws:Referer condition SES requires on its receipt-rule S3 action). Normally the same account this is deployed into."
  type        = string
}

variable "agent_session_ia_transition_days" {
  description = "Days before session objects move to S3 Standard-IA (cheaper per-GB, small retrieval cost) - 30 is S3's own minimum eligible age for this transition."
  type        = number
  default     = 30
}

variable "agent_session_retention_days" {
  description = "Days before session objects are deleted outright. Must be greater than agent_session_ia_transition_days."
  type        = number
  default     = 90
}
