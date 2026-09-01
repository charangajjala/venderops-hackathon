variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "ses_domain" {
  description = "Domain SES receives mail for, e.g. \"pixelbuffer.com\". Verification and DKIM records still need to be added at the DNS provider - this module only creates the AWS-side identity and outputs the tokens."
  type        = string
}

variable "receipt_rule_recipients" {
  description = "Addresses or domains this receipt rule matches, e.g. [\"rfqs@pixelbuffer.com\"] or [\"pixelbuffer.com\"] to catch everything on the domain."
  type        = list(string)
}

variable "raw_emails_bucket_name" {
  type = string
}

variable "raw_emails_object_key_prefix" {
  type    = string
  default = "inbound"
}

variable "sqs_visibility_timeout_seconds" {
  type    = number
  default = 300
}

variable "sqs_message_retention_seconds" {
  type    = number
  default = 345600
}

variable "dlq_message_retention_seconds" {
  type    = number
  default = 1209600
}

variable "dlq_max_receive_count" {
  type    = number
  default = 5
}
