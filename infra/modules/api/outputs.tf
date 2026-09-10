output "api_endpoint" {
  value = aws_apigatewayv2_stage.dashboard.invoke_url
}

output "dashboard_api_function_name" {
  value = aws_lambda_function.dashboard_api.function_name
}
