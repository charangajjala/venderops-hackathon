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
  table_arns = [
    "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.inventory_table_name}",
    "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.vendors_table_name}",
    "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.rfqs_table_name}",
    "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.open_rfqs_table_name}",
    "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.quotes_table_name}",
    "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.purchase_orders_table_name}",
  ]
}

data "archive_file" "dashboard_api" {
  type        = "zip"
  source_dir  = var.lambda_source_dir
  output_path = "${path.module}/build/dashboard_api.zip"
}

data "aws_iam_policy_document" "dashboard_api_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "dashboard_api" {
  name               = "${local.name_prefix}-dashboard-api"
  assume_role_policy = data.aws_iam_policy_document.dashboard_api_assume_role.json
}

data "aws_iam_policy_document" "dashboard_api_permissions" {
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
    sid    = "TableReadWrite"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Scan",
      "dynamodb:Query",
    ]
    resources = local.table_arns
  }

  statement {
    sid       = "SendEmail"
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "dashboard_api" {
  name   = "${local.name_prefix}-dashboard-api"
  role   = aws_iam_role.dashboard_api.id
  policy = data.aws_iam_policy_document.dashboard_api_permissions.json
}

resource "aws_lambda_function" "dashboard_api" {
  function_name    = "${local.name_prefix}-dashboard-api"
  role             = aws_iam_role.dashboard_api.arn
  handler          = "handler.handler"
  runtime          = "python3.13"
  timeout          = 30
  filename         = data.archive_file.dashboard_api.output_path
  source_code_hash = data.archive_file.dashboard_api.output_base64sha256

  environment {
    variables = {
      INVENTORY_TABLE       = var.inventory_table_name
      VENDORS_TABLE         = var.vendors_table_name
      RFQS_TABLE            = var.rfqs_table_name
      OPEN_RFQS_TABLE       = var.open_rfqs_table_name
      QUOTES_TABLE          = var.quotes_table_name
      PURCHASE_ORDERS_TABLE = var.purchase_orders_table_name
      WRITE_API_KEY         = var.write_api_key
    }
  }

  tags = {
    Name      = "${local.name_prefix}-dashboard-api"
    Component = "dashboard"
  }
}

resource "aws_cloudwatch_log_group" "dashboard_api" {
  name              = "/aws/lambda/${aws_lambda_function.dashboard_api.function_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name      = "${local.name_prefix}-dashboard-api-logs"
    Component = "dashboard"
  }
}

resource "aws_apigatewayv2_api" "dashboard" {
  name          = "${local.name_prefix}-dashboard-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "X-Api-Key"]
  }
}

resource "aws_apigatewayv2_stage" "dashboard" {
  api_id      = aws_apigatewayv2_api.dashboard.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "dashboard_api" {
  api_id                 = aws_apigatewayv2_api.dashboard.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.dashboard_api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_inventory" {
  api_id    = aws_apigatewayv2_api.dashboard.id
  route_key = "GET /inventory"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api.id}"
}

resource "aws_apigatewayv2_route" "get_vendors" {
  api_id    = aws_apigatewayv2_api.dashboard.id
  route_key = "GET /vendors"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api.id}"
}

resource "aws_apigatewayv2_route" "get_rfqs" {
  api_id    = aws_apigatewayv2_api.dashboard.id
  route_key = "GET /rfqs"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api.id}"
}

resource "aws_apigatewayv2_route" "get_purchase_orders" {
  api_id    = aws_apigatewayv2_api.dashboard.id
  route_key = "GET /purchase-orders"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api.id}"
}

resource "aws_apigatewayv2_route" "post_adjust_inventory" {
  api_id    = aws_apigatewayv2_api.dashboard.id
  route_key = "POST /inventory/{sku}/adjust"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api.id}"
}

resource "aws_apigatewayv2_route" "post_approve" {
  api_id    = aws_apigatewayv2_api.dashboard.id
  route_key = "POST /rfqs/{rfq_id}/approve"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api.id}"
}

resource "aws_apigatewayv2_route" "post_reject" {
  api_id    = aws_apigatewayv2_api.dashboard.id
  route_key = "POST /rfqs/{rfq_id}/reject"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api.id}"
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dashboard_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.dashboard.execution_arn}/*/*"
}
