# AWS DYNAMODB TABLE FOR VISITOR COUNTER

resource "aws_dynamodb_table" "visitor_counter" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  # Prevent accidental deletion of visitor data
  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name = "CloudResume Visitor Counter"
  }
}


# AWS LAMBDA FUNCTION AND IAM ROLE FOR VISITOR COUNTER

resource "aws_iam_role" "visitor_counter_role" {
  name = "visitor-counter-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Principal = { Service = "lambda.amazonaws.com" },
      Effect    = "Allow",
    }]
  })
}

resource "aws_iam_role_policy" "visitor_counter_policy" {
  role = aws_iam_role.visitor_counter_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ],
        Resource = aws_dynamodb_table.visitor_counter.arn
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      },
      {
        Effect   = "Allow",
        Action   = "sns:Publish",
        Resource = aws_sns_topic.visitor_alerts.arn
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject"
        ],
        Resource = "${aws_s3_bucket.resume_bucket.arn}/*"
      }
    ]
  })
}

# AWS SNS TOPIC FOR VISITOR ALERTS
resource "aws_sns_topic" "visitor_alerts" {
  name = var.sns_topic_name
}

resource "aws_sns_topic_subscription" "visitor_alerts_email" {
  topic_arn = aws_sns_topic.visitor_alerts.arn
  protocol  = "email"
  endpoint  = "work@${var.domain_name}" # Replace with your email
}

resource "aws_lambda_function" "visitor_counter" {
  function_name = "visitor-counter"
  role          = aws_iam_role.visitor_counter_role.arn
  runtime       = "python3.12"
  handler       = "lambda_function.lambda_handler"

  filename         = "${path.module}/../lambda/lambda_function.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda/lambda_function.zip")

  environment {
    variables = {
      DYNAMODB_TABLE       = aws_dynamodb_table.visitor_counter.name
      RECAPTCHA_SECRET_KEY = var.recaptcha_secret_key
      SNS_TOPIC_ARN        = aws_sns_topic.visitor_alerts.arn
      RESUME_BUCKET_NAME   = aws_s3_bucket.resume_bucket.id
      RESUME_FILE_KEY      = "resume.pdf"
    }
  }

  timeout = 30
}

# AWS API GATEWAY V2 INTEGRATION WITH LAMBDA

resource "aws_apigatewayv2_api" "visitor_api" {
  name          = "visitor-counter-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["https://${var.domain_name}"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type"]
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.visitor_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.visitor_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.visitor_counter.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "visitor_count_route" {
  api_id    = aws_apigatewayv2_api.visitor_api.id
  route_key = "POST /count"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "resume_download_route" {
  api_id    = aws_apigatewayv2_api.visitor_api.id
  route_key = "POST /resume-download"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_lambda_permission" "allow_apigw_to_invoke_lambda" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.visitor_counter.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.visitor_api.execution_arn}/*/*"
}

# CUSTOM DOMAIN FOR API GATEWAY

resource "aws_apigatewayv2_domain_name" "api_domain" {
  domain_name = "api.${var.domain_name}"

  domain_name_configuration {
    certificate_arn = aws_acm_certificate.api_cert.arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  depends_on = [aws_acm_certificate_validation.api_cert_valid]
}

resource "aws_apigatewayv2_api_mapping" "api_mapping" {
  api_id      = aws_apigatewayv2_api.visitor_api.id
  domain_name = aws_apigatewayv2_domain_name.api_domain.id
  stage       = aws_apigatewayv2_stage.default.id
}
