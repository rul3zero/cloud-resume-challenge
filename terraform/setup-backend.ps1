# Setup Terraform remote state backend
# Run this once to create the S3 bucket and DynamoDB table

$BUCKET_NAME = "joshcarl-terraform-state"
$TABLE_NAME = "terraform-state-lock"
$REGION = "ap-southeast-1"

Write-Host "Creating S3 bucket for Terraform state..."

# Create S3 bucket for state
aws s3api create-bucket `
  --bucket $BUCKET_NAME `
  --region $REGION `
  --create-bucket-configuration LocationConstraint=$REGION

# Enable versioning on the bucket
Write-Host "Enabling versioning..."
aws s3api put-bucket-versioning `
  --bucket $BUCKET_NAME `
  --versioning-configuration Status=Enabled

# Enable server-side encryption
Write-Host "Enabling encryption..."
aws s3api put-bucket-encryption `
  --bucket $BUCKET_NAME `
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block public access
Write-Host "Blocking public access..."
aws s3api put-public-access-block `
  --bucket $BUCKET_NAME `
  --public-access-block-configuration `
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Create DynamoDB table for state locking
Write-Host "Creating DynamoDB table for state locking..."
aws dynamodb create-table `
  --table-name $TABLE_NAME `
  --attribute-definitions AttributeName=LockID,AttributeType=S `
  --key-schema AttributeName=LockID,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST `
  --region $REGION

Write-Host ""
Write-Host "Backend setup complete!" -ForegroundColor Green
Write-Host "Bucket: $BUCKET_NAME"
Write-Host "DynamoDB Table: $TABLE_NAME"
Write-Host ""
Write-Host "Now run: terraform init -reconfigure" -ForegroundColor Yellow
