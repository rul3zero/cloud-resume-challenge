terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.0.0"

  # Remote state backend for CI/CD
  backend "s3" {
    bucket         = "joshcarl-terraform-state"
    key            = "cloudresume-backend/terraform.tfstate"
    region         = "ap-southeast-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = "ap-southeast-1" # (Singapore)
  alias  = "ap_southeast_1"
}

provider "aws" {
  region = "us-east-1" # (N. Virgina) For CloudFront ACM cert validation
  alias  = "us_east_1"
}
