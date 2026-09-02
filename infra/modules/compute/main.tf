terraform {
  required_providers {
    archive = {
      source = "hashicorp/archive"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  name_prefix = "${var.project}-${var.environment}"
}

data "archive_file" "reorder_checker" {
  type        = "zip"
  source_dir  = var.lambda_source_dir
  output_path = "${path.module}/build/reorder_checker.zip"
}

data "aws_iam_policy_document" "reorder_checker_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "reorder_checker" {
  name               = "${local.name_prefix}-reorder-checker"
  assume_role_policy = data.aws_iam_policy_document.reorder_checker_assume_role.json
}

data "aws_iam_policy_document" "reorder_checker_permissions" {
  statement {
    sid    = "Logs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "DynamoDBStreamRead"
    effect = "Allow"
    actions = [
      "dynamodb:GetRecords",
      "dynamodb:GetShardIterator",
      "dynamodb:DescribeStream",
      "dynamodb:ListStreams",
    ]
    resources = [var.inventory_table_stream_arn]
  }

  statement {
    sid       = "OpenRfqsRead"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = ["arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.open_rfqs_table_name}"]
  }

  statement {
    sid     = "InvokeAgentRuntime"
    effect  = "Allow"
    actions = ["bedrock-agentcore:InvokeAgentRuntime"]
    resources = [
      var.agent_runtime_arn,
      "${var.agent_runtime_arn}/runtime-endpoint/*",
    ]
  }
}

resource "aws_iam_role_policy" "reorder_checker" {
  name   = "${local.name_prefix}-reorder-checker"
  role   = aws_iam_role.reorder_checker.id
  policy = data.aws_iam_policy_document.reorder_checker_permissions.json
}

resource "aws_lambda_function" "reorder_checker" {
  function_name    = "${local.name_prefix}-reorder-checker"
  role             = aws_iam_role.reorder_checker.arn
  handler          = "handler.handler"
  runtime          = "python3.13"
  timeout          = 120
  filename         = data.archive_file.reorder_checker.output_path
  source_code_hash = data.archive_file.reorder_checker.output_base64sha256

  environment {
    variables = {
      OPEN_RFQS_TABLE   = var.open_rfqs_table_name
      AGENT_RUNTIME_ARN = var.agent_runtime_arn
    }
  }

  tags = {
    Name      = "${local.name_prefix}-reorder-checker"
    Component = "reorder-trigger"
  }
}

resource "aws_lambda_event_source_mapping" "inventory_stream" {
  event_source_arn  = var.inventory_table_stream_arn
  function_name     = aws_lambda_function.reorder_checker.arn
  starting_position = "LATEST"
  batch_size        = 10
}

data "archive_file" "service" {
  type        = "zip"
  source_dir  = var.service_lambda_source_dir
  output_path = "${path.module}/build/service.zip"
}

data "aws_iam_policy_document" "service_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "service" {
  name               = "${local.name_prefix}-service"
  assume_role_policy = data.aws_iam_policy_document.service_assume_role.json
}

data "aws_iam_policy_document" "service_permissions" {
  statement {
    sid    = "Logs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "SqsConsume"
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [var.inbound_email_queue_arn]
  }

  statement {
    sid       = "ReadRawEmails"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${var.raw_emails_bucket_arn}/*"]
  }

  statement {
    sid    = "IdempotencyTable"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
    ]
    resources = ["arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.idempotency_table_name}"]
  }

  statement {
    sid     = "InvokeAgentRuntime"
    effect  = "Allow"
    actions = ["bedrock-agentcore:InvokeAgentRuntime"]
    resources = [
      var.agent_runtime_arn,
      "${var.agent_runtime_arn}/runtime-endpoint/*",
    ]
  }
}

resource "aws_iam_role_policy" "service" {
  name   = "${local.name_prefix}-service"
  role   = aws_iam_role.service.id
  policy = data.aws_iam_policy_document.service_permissions.json
}

resource "aws_lambda_function" "service" {
  function_name    = "${local.name_prefix}-service"
  role             = aws_iam_role.service.arn
  handler          = "handler.handler"
  runtime          = "python3.13"
  timeout          = 120
  filename         = data.archive_file.service.output_path
  source_code_hash = data.archive_file.service.output_base64sha256

  environment {
    variables = {
      RAW_EMAILS_BUCKET = var.raw_emails_bucket_name
      AGENT_RUNTIME_ARN = var.agent_runtime_arn
      IDEMPOTENCY_TABLE = var.idempotency_table_name
    }
  }

  tags = {
    Name      = "${local.name_prefix}-service"
    Component = "email-processing"
  }
}

resource "aws_lambda_event_source_mapping" "inbound_email_queue" {
  event_source_arn = var.inbound_email_queue_arn
  function_name    = aws_lambda_function.service.arn
  batch_size       = 1
}
