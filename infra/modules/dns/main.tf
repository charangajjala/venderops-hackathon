terraform {
  required_providers {
    cloudflare = {
      source = "cloudflare/cloudflare"
    }
  }
}

resource "cloudflare_dns_record" "ses_verification" {
  zone_id = var.cloudflare_zone_id
  name    = "_amazonses.${var.domain}"
  type    = "TXT"
  content = var.ses_domain_verification_token
  ttl     = var.ttl
  proxied = false
}

resource "cloudflare_dns_record" "ses_dkim" {
  for_each = toset(["0", "1", "2"])

  zone_id = var.cloudflare_zone_id
  name    = "${var.ses_dkim_tokens[tonumber(each.value)]}._domainkey.${var.domain}"
  type    = "CNAME"
  content = "${var.ses_dkim_tokens[tonumber(each.value)]}.dkim.amazonses.com"
  ttl     = var.ttl
  proxied = false
}

resource "cloudflare_dns_record" "ses_mx" {
  zone_id  = var.cloudflare_zone_id
  name     = var.domain
  type     = "MX"
  content  = var.ses_mx_target
  priority = var.ses_mx_priority
  ttl      = var.ttl
  proxied  = false
}

resource "cloudflare_dns_record" "ses_spf" {
  count = var.add_spf_record ? 1 : 0

  zone_id = var.cloudflare_zone_id
  name    = var.domain
  type    = "TXT"
  content = "v=spf1 include:amazonses.com ~all"
  ttl     = var.ttl
  proxied = false
}
