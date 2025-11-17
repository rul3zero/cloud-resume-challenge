output "a_records" {
  value = [
    aws_route53_record.cloudfront_alias.name,
    aws_route53_record.a_record_h9gqczx4ir8x.name
  ]
  description = "Names of A records in the hosted zone"
}

output "cloudfront_domain_name" {
  value       = aws_cloudfront_distribution.main.domain_name
  description = "The domain name of the CloudFront Distribution"
}

output "s3_bucket_name" {
  value = aws_s3_bucket.cloudresume_bucket.id
}

output "cloudfront_distribution_id" {
  value       = aws_cloudfront_distribution.main.id
  description = "The ID of the CloudFront Distribution"
}

output "oac_id" {
  value       = aws_cloudfront_origin_access_control.main.id
  description = "The ID of the Origin Access Control"
}


output "route53_zone_id" {
  value       = data.aws_route53_zone.cloudresume_zone.zone_id
  description = "The ID of the Route 53 Hosted Zone."
}

output "route53_name_servers" {
  value       = data.aws_route53_zone.cloudresume_zone.name_servers
  description = "Name servers for the hosted zone (already configured at registrar)"
}

output "lambda_function_name" {
  value       = aws_lambda_function.visitor_counter.function_name
  description = "The name of the Visitor Counter Lambda function"
}

output "api_gateway_invoke_url" {
  value       = "https://${aws_apigatewayv2_domain_name.api_domain.domain_name}/count"
  description = "The custom domain URL of the API Gateway"
}