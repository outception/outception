variable "environment" {
  description = "Environment name"
  type        = string

  validation {
    condition     = contains(["production"], var.environment)
    error_message = "Must be \"production\"."
  }
}

variable "logs_bucket_name" {
  description = "Name of the S3 bucket containing span logs"
  type        = string
}
