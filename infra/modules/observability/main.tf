terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.billing]
    }
  }
}

locals {
  name_prefix = "${var.project}-${var.environment}"
}

resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"

  tags = {
    Name      = "${local.name_prefix}-alerts"
    Component = "operational-alerts"
  }
}

resource "aws_sns_topic_subscription" "alerts_email" {
  for_each  = toset(var.alert_emails)
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

resource "aws_budgets_budget" "monthly_cost" {
  name         = "${local.name_prefix}-monthly-cost"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  tags = {
    Name      = "${local.name_prefix}-monthly-cost"
    Component = "budget-guardrail"
  }

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 50
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.alerts.arn]
  }

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.alerts.arn]
  }

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.alerts.arn]
  }

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "FORECASTED"
    subscriber_sns_topic_arns = [aws_sns_topic.alerts.arn]
  }
}

resource "aws_sns_topic" "billing_alerts" {
  provider = aws.billing
  name     = "${local.name_prefix}-billing-alerts"

  tags = {
    Name      = "${local.name_prefix}-billing-alerts"
    Component = "billing-alarm"
  }
}

resource "aws_sns_topic_subscription" "billing_alerts_email" {
  for_each  = toset(var.alert_emails)
  provider  = aws.billing
  topic_arn = aws_sns_topic.billing_alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

resource "aws_cloudwatch_metric_alarm" "billing_threshold" {
  for_each = toset([for t in var.cloudwatch_billing_alarm_thresholds_usd : tostring(t)])
  provider = aws.billing

  alarm_name          = "${local.name_prefix}-billing-over-${each.value}-usd"
  alarm_description   = "Estimated AWS charges have exceeded $${each.value} against the $${var.monthly_budget_usd} hackathon credit."
  namespace           = "AWS/Billing"
  metric_name         = "EstimatedCharges"
  dimensions          = { Currency = "USD" }
  statistic           = "Maximum"
  period              = 21600
  evaluation_periods  = 1
  threshold           = tonumber(each.value)
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.billing_alerts.arn]

  tags = {
    Name      = "${local.name_prefix}-billing-over-${each.value}-usd"
    Component = "billing-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "dlq_depth" {
  for_each = toset(var.dlq_names)

  alarm_name          = "${local.name_prefix}-dlq-${each.value}-nonempty"
  alarm_description   = "Dead-letter queue ${each.value} has at least one message - something exhausted its retries and needs a human look."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = each.value }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = {
    Name      = "${local.name_prefix}-dlq-${each.value}-nonempty"
    Component = "operational-alerts"
  }
}

resource "aws_cloudwatch_metric_alarm" "queue_backlog" {
  for_each = toset(var.backlog_queues)

  alarm_name          = "${local.name_prefix}-backlog-${each.value}"
  alarm_description   = "Queue ${each.value} has a message older than ${var.backlog_age_threshold_seconds}s - the consumer has stopped keeping up."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  dimensions          = { QueueName = each.value }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.backlog_age_threshold_seconds
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = {
    Name      = "${local.name_prefix}-backlog-${each.value}"
    Component = "operational-alerts"
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = toset(var.lambda_function_names)

  alarm_name          = "${local.name_prefix}-lambda-errors-${each.value}"
  alarm_description   = "Lambda ${each.value} has thrown at least one error in the last 5 minutes."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = each.value }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = {
    Name      = "${local.name_prefix}-lambda-errors-${each.value}"
    Component = "operational-alerts"
  }
}

resource "aws_cloudwatch_metric_alarm" "ses_bounce" {
  count = var.enable_ses_alarms ? 1 : 0

  alarm_name          = "${local.name_prefix}-ses-bounce"
  alarm_description   = "SES has recorded at least one bounce in the last 5 minutes - repeated bounces risk sending reputation / account health."
  namespace           = "AWS/SES"
  metric_name         = "Bounce"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = {
    Name      = "${local.name_prefix}-ses-bounce"
    Component = "operational-alerts"
  }
}

resource "aws_cloudwatch_metric_alarm" "ses_complaint" {
  count = var.enable_ses_alarms ? 1 : 0

  alarm_name          = "${local.name_prefix}-ses-complaint"
  alarm_description   = "SES has recorded at least one spam complaint in the last 5 minutes - repeated complaints risk sending reputation / account health."
  namespace           = "AWS/SES"
  metric_name         = "Complaint"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = {
    Name      = "${local.name_prefix}-ses-complaint"
    Component = "operational-alerts"
  }
}
