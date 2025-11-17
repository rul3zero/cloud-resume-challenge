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



