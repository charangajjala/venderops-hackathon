locals {
  name_prefix = "${var.project}-${var.environment}"
}

resource "aws_s3_bucket" "raw_emails" {
  bucket = "${local.name_prefix}-raw-emails"

  tags = {
    Name      = "${local.name_prefix}-raw-emails"
    Component = "email-ingestion"
  }
}

resource "aws_s3_bucket_public_access_block" "raw_emails" {
  bucket = aws_s3_bucket.raw_emails.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_emails" {
  bucket = aws_s3_bucket.raw_emails.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "raw_emails" {
  bucket = aws_s3_bucket.raw_emails.id

  rule {
    id     = "expire-raw-emails"
    status = "Enabled"

    filter {}

    expiration {
      days = var.raw_email_retention_days
    }
  }
}

data "aws_iam_policy_document" "raw_emails_ses_write" {
  statement {
    sid    = "AllowSESPuts"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ses.amazonaws.com"]
    }

    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.raw_emails.arn}/*"]

    condition {
      test     = "StringEquals"
      variable = "aws:Referer"
      values   = [var.ses_allowed_account_id]
    }
  }
}

resource "aws_s3_bucket_policy" "raw_emails" {
  bucket = aws_s3_bucket.raw_emails.id
  policy = data.aws_iam_policy_document.raw_emails_ses_write.json
}

resource "aws_s3_bucket" "agent_sessions" {
  bucket = "${local.name_prefix}-agent-sessions"

  tags = {
    Name      = "${local.name_prefix}-agent-sessions"
    Component = "agentcore-session-store"
  }
}

resource "aws_s3_bucket_public_access_block" "agent_sessions" {
  bucket = aws_s3_bucket.agent_sessions.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "agent_sessions" {
  bucket = aws_s3_bucket.agent_sessions.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "agent_sessions" {
  bucket = aws_s3_bucket.agent_sessions.id

  rule {
    id     = "transition-then-expire-sessions"
    status = "Enabled"

    filter {}

    transition {
      days          = var.agent_session_ia_transition_days
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = var.agent_session_retention_days
    }
  }
}
