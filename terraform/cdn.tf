# AWS CLOUDFRONT
resource "aws_cloudfront_origin_access_control" "main" {
  name                              = "cloud-resume-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
  description                       = "OAC for Cloud Resume CloudFront"
}

resource "aws_cloudfront_function" "url_rewrite" {
  name    = "url-rewrite-function"
  runtime = "cloudfront-js-2.0"
  comment = "Append index.html to directory requests"
  publish = true
  code    = <<-EOT
function handler(event) {
    var request = event.request;
    var uri = request.uri;
    
    // Check if URI ends with '/'
    if (uri.endsWith('/')) {
        request.uri += 'index.html';
    }
    // Check if URI has no file extension
    else if (!uri.includes('.')) {
        request.uri += '/index.html';
    }
    
    return request;
}
EOT
}

resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  default_root_object = "index.html"
  comment             = "Cloud Resume Challenge"

  aliases = [
    var.domain_name,
    "www.${var.domain_name}",
    "*.${var.domain_name}"
  ]

  origin {
    domain_name              = aws_s3_bucket.cloudresume_bucket.bucket_regional_domain_name
    origin_id                = "s3-cloudresume"
    origin_access_control_id = aws_cloudfront_origin_access_control.main.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-cloudresume"
    viewer_protocol_policy = "redirect-to-https"

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.url_rewrite.arn
    }

    forwarded_values {
      cookies { forward = "none" }
      query_string = false
    }
  }

  price_class = "PriceClass_100"

  custom_error_response {
    error_code         = 403
    response_code      = 404
    response_page_path = "/404.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 404
    response_page_path = "/404.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.cloudresume_cert.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}


