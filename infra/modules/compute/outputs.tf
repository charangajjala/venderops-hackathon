output "reorder_checker_function_name" {
  value = aws_lambda_function.reorder_checker.function_name
}

output "reorder_checker_function_arn" {
  value = aws_lambda_function.reorder_checker.arn
}

output "service_function_name" {
  value = aws_lambda_function.service.function_name
}

output "service_function_arn" {
  value = aws_lambda_function.service.arn
}
