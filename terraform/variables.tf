variable "recaptcha_secret_key" {
  description = "Google reCAPTCHA v3 Secret Key"
  type        = string
  sensitive   = true
}

variable "route53_zone_id" {
  description = "Existing Route53 Hosted Zone ID (to avoid recreating NS records)"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the website"
  type        = string
  default     = "joshcarl.dev"
}

variable "s3_bucket_name" {
  description = "S3 bucket name for static website hosting"
  type        = string
  default     = "joshcarl.dev"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for visitor counter"
  type        = string
  default     = "visitor-counter"
}

variable "sns_topic_name" {
  description = "SNS topic name for visitor alerts"
  type        = string
  default     = "visitor-counter-alert"
}

variable "protect_data_resources" {
  description = "Whether to protect data resources from deletion"
  type        = bool
  default     = true
}
