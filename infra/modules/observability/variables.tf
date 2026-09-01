variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "alert_emails" {
  description = "Email addresses to notify for billing/operational alerts. Each gets its own SNS subscription and its own confirmation email that must be clicked before that address receives alerts."
  type        = list(string)

  validation {
    condition     = length(var.alert_emails) > 0
    error_message = "At least one alert_emails address is required, or billing alarms fire into the void."
  }
}

variable "monthly_budget_usd" {
  description = "Monthly AWS Budgets cost limit, in USD. Kept under the $50 hackathon promotional credit on purpose - see infra plan §4."
  type        = number
  default     = 45
}

variable "cloudwatch_billing_alarm_thresholds_usd" {
  description = "Estimated-charges thresholds (USD) to raise a CloudWatch alarm at, in addition to the AWS Budgets alert."
  type        = list(number)
  default     = [10, 25, 40]
}
