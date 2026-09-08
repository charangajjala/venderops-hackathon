output "verification_record_id" {
  value = cloudflare_dns_record.ses_verification.id
}

output "dkim_record_ids" {
  value = [for r in cloudflare_dns_record.ses_dkim : r.id]
}

output "mx_record_id" {
  value = cloudflare_dns_record.ses_mx.id
}
