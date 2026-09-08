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

variable "ecr_keep_image_count" {
  description = "Number of most-recent tagged images to keep in ECR before older ones expire."
  type        = number
  default     = 5
}

variable "log_retention_days" {
  type    = number
  default = 14
}
