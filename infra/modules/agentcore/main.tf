data "aws_caller_identity" "current" {}

locals {
  name_prefix = "${var.project}-${var.environment}"
}

resource "aws_ecr_repository" "agent" {
  name                 = "${local.name_prefix}-agent"
  image_tag_mutability = "MUTABLE"

  tags = {
    Name      = "${local.name_prefix}-agent"
    Component = "agentcore-runtime"
  }
}

resource "aws_ecr_lifecycle_policy" "agent" {
  repository = aws_ecr_repository.agent.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 1 day - they're leftovers from a retag/push, nothing references them by digest."
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep only the most recent ${var.ecr_keep_image_count} tagged images - older ones are superseded deploys, not needed once the runtime has moved past them."
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = var.ecr_keep_image_count
        }
        action = { type = "expire" }
      }
    ]
  })
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "runtime" {
  name               = "${local.name_prefix}-agentcore-runtime"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

data "aws_iam_policy_document" "runtime_permissions" {
  statement {
    sid       = "ECRAuth"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "ECRPull"
    effect = "Allow"
    actions = [
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [aws_ecr_repository.agent.arn]
  }

  statement {
    sid    = "Logs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "BedrockInvoke"
    effect    = "Allow"
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = ["*"]
  }

  statement {
    sid    = "DynamoDBTables"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
    ]
    resources = [
      "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${local.name_prefix}-*",
    ]
  }

  statement {
    sid    = "AgentSessionsBucket"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:DeleteObject",
    ]
    resources = [
      var.agent_sessions_bucket_arn,
      "${var.agent_sessions_bucket_arn}/*",
    ]
  }

  statement {
    sid       = "SendVendorEmails"
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "runtime" {
  name   = "${local.name_prefix}-agentcore-runtime"
  role   = aws_iam_role.runtime.id
  policy = data.aws_iam_policy_document.runtime_permissions.json
}

resource "aws_bedrockagentcore_agent_runtime" "vendorops" {
  agent_runtime_name = replace("${local.name_prefix}_agent", "-", "_")
  role_arn           = aws_iam_role.runtime.arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.agent.repository_url}:${var.image_tag}"
    }
  }

  environment_variables = {
    PROJECT               = var.project
    ENVIRONMENT           = var.environment
    AWS_REGION            = var.aws_region
    AGENT_SESSIONS_BUCKET = replace(var.agent_sessions_bucket_arn, "arn:aws:s3:::", "")
  }

  network_configuration {
    network_mode = "PUBLIC"
  }
}

resource "aws_cloudwatch_log_group" "agentcore_runtime" {
  name              = "/aws/bedrock-agentcore/runtimes/${aws_bedrockagentcore_agent_runtime.vendorops.agent_runtime_id}-DEFAULT"
  retention_in_days = var.log_retention_days

  tags = {
    Name      = "${local.name_prefix}-agentcore-runtime-logs"
    Component = "agentcore-runtime"
  }
}

import {
  to = aws_cloudwatch_log_group.agentcore_runtime
  id = "/aws/bedrock-agentcore/runtimes/${aws_bedrockagentcore_agent_runtime.vendorops.agent_runtime_id}-DEFAULT"
}
