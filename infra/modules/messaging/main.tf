locals {
  name_prefix = "${var.project}-${var.environment}"
}

resource "aws_ses_domain_identity" "this" {
  domain = var.ses_domain
}

resource "aws_ses_domain_dkim" "this" {
  domain = aws_ses_domain_identity.this.domain
}

resource "aws_sns_topic" "inbound_email" {
  name = "${local.name_prefix}-inbound-email"

  tags = {
    Name      = "${local.name_prefix}-inbound-email"
    Component = "email-ingestion"
  }
}

resource "aws_sqs_queue" "inbound_email_dlq" {
  name                      = "${local.name_prefix}-inbound-email-dlq"
  message_retention_seconds = var.dlq_message_retention_seconds

  tags = {
    Name      = "${local.name_prefix}-inbound-email-dlq"
    Component = "email-ingestion"
  }
}

resource "aws_sqs_queue" "inbound_email" {
  name                       = "${local.name_prefix}-inbound-email"
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds
  message_retention_seconds  = var.sqs_message_retention_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.inbound_email_dlq.arn
    maxReceiveCount     = var.dlq_max_receive_count
  })

  tags = {
    Name      = "${local.name_prefix}-inbound-email"
    Component = "email-ingestion"
  }
}

data "aws_iam_policy_document" "inbound_email_queue_policy" {
  statement {
    sid    = "AllowSNSPublish"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["sns.amazonaws.com"]
    }

    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.inbound_email.arn]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_sns_topic.inbound_email.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "inbound_email" {
  queue_url = aws_sqs_queue.inbound_email.id
  policy    = data.aws_iam_policy_document.inbound_email_queue_policy.json
}

resource "aws_sns_topic_subscription" "inbound_email_to_sqs" {
  topic_arn            = aws_sns_topic.inbound_email.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.inbound_email.arn
  raw_message_delivery = true
}

resource "aws_ses_receipt_rule_set" "main" {
  rule_set_name = "${local.name_prefix}-rules"
}

resource "aws_ses_active_receipt_rule_set" "main" {
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
}

resource "aws_ses_receipt_rule" "inbound" {
  name          = "${local.name_prefix}-inbound"
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
  recipients    = var.receipt_rule_recipients
  enabled       = true
  scan_enabled  = true

  s3_action {
    bucket_name       = var.raw_emails_bucket_name
    object_key_prefix = var.raw_emails_object_key_prefix
    position          = 1
  }

  sns_action {
    topic_arn = aws_sns_topic.inbound_email.arn
    position  = 2
  }
}
