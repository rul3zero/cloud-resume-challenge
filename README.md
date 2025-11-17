# Cloud Resume Challenge

This is my attempt at the [Cloud Resume Challenge](https://cloudresumechallenge.dev/) using Terraform for Infrastructure as Code. I built the full architecture from frontend to backend from scratch with added improvements in visitor count like:
- Bot protection using Google reCAPTCHA v3
- Duplicate visitor detection
- SNS notifications and alerts
 
## Live Demo

**Website**: 🌐 [joshcarl.dev](https://joshcarl.dev) 
**API Endpoint**: [api.joshcarl.dev/count](https://api.joshcarl.dev/count)

## Tech Stack

**Infrastructure & Deployment**
- Terraform (IaC)
- GitHub Actions (CI/CD)

**AWS Services**
- S3 (Static hosting)
- CloudFront (CDN)
- Route53 (DNS)
- API Gateway (REST API)
- Lambda (Serverless compute)
- DynamoDB (NoSQL database)
- SNS (Notifications)
- ACM (SSL/TLS certificates)
- IAM (Access management)

**Security**
- Google reCAPTCHA v3 (Bot protection)
- IP-based rate limiting (DynamoDB TTL)
- CloudFront OAC (Origin Access Control)
- HTTPS/TLS 1.2+ (Encryption in transit)
- IAM least privilege roles

**Development**
- Python
- boto3 (AWS SDK)
- pytest (Unit testing)

## Repository Structure

```
cloudresume-backend/
├── .github/
│   └── workflows/
│       └── deploy-backend.yml    # CI/CD pipeline
├── lambda/
│   ├── lambda_function.py        # Visitor counter API
│   └── lambda_function.zip       # Deployment package
├── terraform/
│   ├── api.tf                    # API Gateway, Lambda, DynamoDB, SNS
│   ├── cdn.tf                    # CloudFront distribution
│   ├── dns.tf                    # Route53 and ACM certificates
│   ├── storage.tf                # S3 bucket configuration
│   ├── main.tf                   # Provider and backend configuration
│   ├── variables.tf              # Variable definitions
│   ├── outputs.tf                # Output values
│   ├── setup-backend.ps1         # Script to create S3/DynamoDB for remote state
│   └── setup-backend.sh          # Bash version of backend setup
├── tests/
│   ├── __init__.py
│   └── test_lambda_function.py   # Python unit tests
├── .gitignore
└── README.md
```

## Terraform Remote State Backend

This project uses S3 for remote state storage with DynamoDB for state locking, enabling CI/CD deployments:

**Backend Resources:**
- S3 Bucket: `joshcarl-terraform-state`
- DynamoDB Table: `terraform-state-lock`
- Region: `ap-southeast-1`

**Initial Setup (One-time):**
```powershell
# Run the setup script to create backend resources
cd terraform
.\setup-backend.ps1

# Initialize Terraform with the backend
terraform init -migrate-state
```

## Environment Variables

**Local Development (`terraform.tfvars`):**

```terraform
recaptcha_secret_key = "your-google-recaptcha-v3-secret-key"
route53_zone_id      = "your-existing-zone-id"
```

## GitHub Secrets (Required for CI/CD)
```
AWS_ACCESS_KEY_ID         # AWS access key
AWS_SECRET_ACCESS_KEY     # AWS secret access key
RECAPTCHA_SECRET_KEY      # Google reCAPTCHA v3 secret key
ROUTE53_ZONE_ID           # Existing Route53 hosted zone ID
```

## Cost Estimate

My estimated monthly costs on my website traffic:

| Service | Estimated Cost |
|---------|----------------|
| Route53 Hosted Zone | $0.50 |
| S3 Storage & Requests | ~$0.01 |
| CloudFront | Free tier / ~$0.10 |
| Lambda Invocations | Free tier |
| DynamoDB | Free tier |
| API Gateway | Free tier |
| SNS | Free tier |
| ACM Certificates | Free |
| Tax | ~$0.06 |

My estimated costs ranges from ~$0.50-1.00 per month with tax included.

## Frontend Repository

You can checkout the frontend here: **[https://github.com/rul3zero/cloud-resume-challenge-frontend](https://github.com/rul3zero/cloud-resume-challenge-frontend)**