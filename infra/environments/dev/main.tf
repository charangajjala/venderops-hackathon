module "storage" {
  source = "../../modules/storage"

  project                = var.project
  environment            = var.environment
  ses_allowed_account_id = data.aws_caller_identity.current.account_id
}

module "observability" {
  source = "../../modules/observability"
  providers = {
    aws         = aws
    aws.billing = aws.billing
  }

  project            = var.project
  environment        = var.environment
  alert_emails       = var.alert_emails
  monthly_budget_usd = var.monthly_budget_usd
}

module "messaging" {
  source = "../../modules/messaging"

  depends_on = [module.storage]

  project                 = var.project
  environment             = var.environment
  ses_domain              = var.ses_domain
  receipt_rule_recipients = var.receipt_rule_recipients
  raw_emails_bucket_name  = module.storage.raw_emails_bucket_name
  sandbox_test_recipients = var.ses_sandbox_test_recipients
}

module "dynamodb" {
  source = "../../modules/dynamodb"

  project     = var.project
  environment = var.environment
  vendors     = var.vendors
}

module "dns" {
  source = "../../modules/dns"

  cloudflare_zone_id            = var.cloudflare_zone_id
  domain                        = var.ses_domain
  ses_domain_verification_token = module.messaging.ses_domain_verification_token
  ses_dkim_tokens               = module.messaging.ses_dkim_tokens
  ses_mx_target                 = "inbound-smtp.${var.aws_region}.amazonaws.com"
}

module "agentcore" {
  source = "../../modules/agentcore"

  project                   = var.project
  environment               = var.environment
  aws_region                = var.aws_region
  agent_sessions_bucket_arn = module.storage.agent_sessions_bucket_arn
}

module "compute" {
  source = "../../modules/compute"

  project                    = var.project
  environment                = var.environment
  aws_region                 = var.aws_region
  inventory_table_stream_arn = module.dynamodb.inventory_table_stream_arn
  open_rfqs_table_name       = module.dynamodb.open_rfqs_table_name
  agent_runtime_arn          = module.agentcore.agent_runtime_arn
  lambda_source_dir          = "${path.module}/../../../lambda_functions/reorder_checker"
}
