# AWS ROUTE 53 - Use existing hosted zone
data "aws_route53_zone" "cloudresume_zone" {
  zone_id = var.route53_zone_id
}

# ACM Certificate for CloudFront (us-east-1)
resource "aws_acm_certificate" "cloudresume_cert" {
  provider          = aws.us_east_1
  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = [
    "www.${var.domain_name}",
    "*.${var.domain_name}"
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# ACM Certificate for API Gateway (ap-southeast-1)
resource "aws_acm_certificate" "api_cert" {
  domain_name       = "api.${var.domain_name}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# Validation records for CloudFront certificate
resource "aws_route53_record" "cloudresume_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cloudresume_cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id         = data.aws_route53_zone.cloudresume_zone.zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 300
  allow_overwrite = true
}

# Validation records for API Gateway certificate
resource "aws_route53_record" "api_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.api_cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id         = data.aws_route53_zone.cloudresume_zone.zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 300
  allow_overwrite = true
}

# Certificate validation
resource "aws_acm_certificate_validation" "cloudresume_cert_valid" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.cloudresume_cert.arn
  validation_record_fqdns = [for record in aws_route53_record.cloudresume_cert_validation : record.fqdn]

  timeouts {
    create = "45m"
  }

  depends_on = [aws_route53_record.cloudresume_cert_validation]
}

resource "aws_acm_certificate_validation" "api_cert_valid" {
  certificate_arn         = aws_acm_certificate.api_cert.arn
  validation_record_fqdns = [for record in aws_route53_record.api_cert_validation : record.fqdn]

  timeouts {
    create = "45m"
  }

  depends_on = [aws_route53_record.api_cert_validation]
}

# CloudFront Alias Record
resource "aws_route53_record" "cloudfront_alias" {
  zone_id = data.aws_route53_zone.cloudresume_zone.id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

# WWW Subdomain Alias
resource "aws_route53_record" "www_alias" {
  zone_id = data.aws_route53_zone.cloudresume_zone.id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

# MX Records
resource "aws_route53_record" "mx_records" {
  zone_id = data.aws_route53_zone.cloudresume_zone.id
  name    = var.domain_name
  type    = "MX"
  ttl     = 300
  records = [
    "10 mx1.improvmx.com",
    "20 mx2.improvmx.com"
  ]
}

# TXT Record
resource "aws_route53_record" "txt_record" {
  zone_id = data.aws_route53_zone.cloudresume_zone.id
  name    = var.domain_name
  type    = "TXT"
  ttl     = 300
  records = ["google-site-verification=helixNCVI9bOkk6xIKG6cD3EaYHzwGGlKngLLif-gSI"]
}

# CNAME Records
resource "aws_route53_record" "cname_s781301_domainkey" {
  zone_id = data.aws_route53_zone.cloudresume_zone.id
  name    = "s781301._domainkey.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = ["dkim.smtp2go.net"]
}

resource "aws_route53_record" "cname_em781301" {
  zone_id = data.aws_route53_zone.cloudresume_zone.id
  name    = "em781301.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = ["return.smtp2go.net"]
}

resource "aws_route53_record" "cname_link" {
  zone_id = data.aws_route53_zone.cloudresume_zone.id
  name    = "link.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = ["track.smtp2go.net"]
}

# A Record
resource "aws_route53_record" "a_record_h5gqczx4ir8x" {
  zone_id = data.aws_route53_zone.cloudresume_zone.id
  name    = "h5gqczx4ir8x.${var.domain_name}"
  type    = "A"
  ttl     = 300
  records = ["20.205.134.55"]
}

# API Gateway Custom Domain A Record
resource "aws_route53_record" "api_domain" {
  zone_id = data.aws_route53_zone.cloudresume_zone.id
  name    = aws_apigatewayv2_domain_name.api_domain.domain_name
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.api_domain.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.api_domain.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}





