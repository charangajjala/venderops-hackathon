output "inventory_table_name" {
  value = aws_dynamodb_table.inventory.name
}

output "inventory_table_stream_arn" {
  value = aws_dynamodb_table.inventory.stream_arn
}

output "vendors_table_name" {
  value = aws_dynamodb_table.vendors.name
}

output "vendor_stock_table_names" {
  value = { for k, v in aws_dynamodb_table.vendor_stock : k => v.name }
}

output "rfqs_table_name" {
  value = aws_dynamodb_table.rfqs.name
}

output "open_rfqs_table_name" {
  value = aws_dynamodb_table.open_rfqs.name
}

output "quotes_table_name" {
  value = aws_dynamodb_table.quotes.name
}

output "purchase_orders_table_name" {
  value = aws_dynamodb_table.purchase_orders.name
}

output "idempotency_table_name" {
  value = aws_dynamodb_table.idempotency.name
}
