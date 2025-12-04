variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
}

variable "project_name" {
  description = "Prefix used for naming AWS resources."
  type        = string
  default     = "robust-data-processor"
}

