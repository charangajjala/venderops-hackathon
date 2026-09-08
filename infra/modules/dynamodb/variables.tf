variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "vendors" {
  description = "Vendor identifiers, each gets its own VendorStock table (VendorStock-<vendor>)."
  type        = list(string)
}
