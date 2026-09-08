output "ecr_repository_url" {
  value = aws_ecr_repository.agent.repository_url
}

output "agent_runtime_arn" {
  value = aws_bedrockagentcore_agent_runtime.vendorops.agent_runtime_arn
}

output "agent_runtime_id" {
  value = aws_bedrockagentcore_agent_runtime.vendorops.agent_runtime_id
}

output "runtime_role_arn" {
  value = aws_iam_role.runtime.arn
}
