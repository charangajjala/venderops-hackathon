variable "cloudflare_zone_id" {
  type = string
}

variable "domain" {
  description = "Domain (or subdomain) SES sends/receives on. Records are created relative to this name."
  type        = string
}

variable "ses_domain_verification_token" {
  type = string
}

variable "ses_dkim_tokens" {
  type = list(string)
}

variable "ses_mx_target" {
  description = "SES inbound SMTP endpoint, e.g. inbound-smtp.us-east-1.amazonaws.com."
  type        = string
}

variable "ses_mx_priority" {
  type    = number
  default = 10
}

variable "add_spf_record" {
  description = "Whether to add an SPF TXT record authorizing SES to send from this domain."
  type        = bool
  default     = true
}

variable "ttl" {
  type    = number
  default = 300
}
