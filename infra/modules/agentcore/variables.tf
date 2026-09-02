variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "agent_sessions_bucket_arn" {
  type = string
}

variable "image_tag" {
  type    = string
  default = "latest"
}
