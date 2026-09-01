locals {
  name_prefix = "${var.project}-${var.environment}"
}

resource "aws_dynamodb_table" "inventory" {
  name         = "${local.name_prefix}-Inventory"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sku"

  attribute {
    name = "sku"
    type = "S"
  }

  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  tags = {
    Name      = "${local.name_prefix}-Inventory"
    Component = "supermarket-inventory"
  }
}

resource "aws_dynamodb_table" "vendors" {
  name         = "${local.name_prefix}-Vendors"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "vendor_id"

  attribute {
    name = "vendor_id"
    type = "S"
  }

  tags = {
    Name      = "${local.name_prefix}-Vendors"
    Component = "vendor-directory"
  }
}

resource "aws_dynamodb_table" "vendor_stock" {
  for_each = toset(var.vendors)

  name         = "${local.name_prefix}-VendorStock-${each.value}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sku"

  attribute {
    name = "sku"
    type = "S"
  }

  tags = {
    Name      = "${local.name_prefix}-VendorStock-${each.value}"
    Component = "vendor-stock"
    Vendor    = each.value
  }
}

resource "aws_dynamodb_table" "rfqs" {
  name         = "${local.name_prefix}-RFQs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "rfq_id"

  attribute {
    name = "rfq_id"
    type = "S"
  }

  tags = {
    Name      = "${local.name_prefix}-RFQs"
    Component = "procurement"
  }
}

resource "aws_dynamodb_table" "open_rfqs" {
  name         = "${local.name_prefix}-OpenRFQs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sku"

  attribute {
    name = "sku"
    type = "S"
  }

  tags = {
    Name      = "${local.name_prefix}-OpenRFQs"
    Component = "procurement"
  }
}

resource "aws_dynamodb_table" "quotes" {
  name         = "${local.name_prefix}-Quotes"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "quote_id"

  attribute {
    name = "quote_id"
    type = "S"
  }

  tags = {
    Name      = "${local.name_prefix}-Quotes"
    Component = "procurement"
  }
}

resource "aws_dynamodb_table" "purchase_orders" {
  name         = "${local.name_prefix}-PurchaseOrders"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "po_id"

  attribute {
    name = "po_id"
    type = "S"
  }

  tags = {
    Name      = "${local.name_prefix}-PurchaseOrders"
    Component = "procurement"
  }
}

resource "aws_dynamodb_table" "idempotency" {
  name         = "${local.name_prefix}-Idempotency"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "message_id"

  attribute {
    name = "message_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name      = "${local.name_prefix}-Idempotency"
    Component = "email-ingestion"
  }
}
