# AWS S3 BUCKET
resource "aws_s3_bucket" "cloudresume_bucket" {
  bucket = var.s3_bucket_name

  # Prevent accidental deletion of website files
  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name        = "CloudResume Static Website"
    Environment = "production"
  }
}

resource "aws_s3_bucket_public_access_block" "cloudresume_bucket" {
  bucket = aws_s3_bucket.cloudresume_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_website_configuration" "cloudresume_site" {
  bucket = aws_s3_bucket.cloudresume_bucket.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "404.html"
  }
}

resource "aws_s3_bucket_policy" "cloudresume_bucket_policy" {
  bucket = aws_s3_bucket.cloudresume_bucket.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "cloudfront.amazonaws.com"
        },
        Action   = "s3:GetObject",
        Resource = "${aws_s3_bucket.cloudresume_bucket.arn}/*",
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.main.arn
          }
        }
      }
    ]
  })
}

# S3 Bucket for Resume Document Storage
resource "aws_s3_bucket" "resume_bucket" {
  bucket = "${var.domain_name}-resume-document"

  tags = {
    Name = "Resume Document Storage"
  }
}

# Block public access to resume bucket
resource "aws_s3_bucket_public_access_block" "resume_bucket" {
  bucket = aws_s3_bucket.resume_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for resume bucket
resource "aws_s3_bucket_versioning" "resume_bucket" {
  bucket = aws_s3_bucket.resume_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption for resume bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "resume_bucket" {
  bucket = aws_s3_bucket.resume_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle rule to transition old versions to cheaper storage
resource "aws_s3_bucket_lifecycle_configuration" "resume_bucket" {
  bucket = aws_s3_bucket.resume_bucket.id

  rule {
    id     = "transition-old-versions"
    status = "Enabled"

    filter {}  # Apply to all objects in the bucket

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}


