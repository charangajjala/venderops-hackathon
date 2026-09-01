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
}

module "dynamodb" {
  source = "../../modules/dynamodb"

  project     = var.project
  environment = var.environment
  vendors     = var.vendors
}
