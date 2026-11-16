terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# AWS Provider Configuration
# IMPORTANT: AWS credentials MUST NOT be hardcoded here.
# Authentication is automatically handled via:
#   1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
#   2. Shared credentials file (~/.aws/credentials or AWS_SHARED_CREDENTIALS_FILE)
#   3. IAM Role / Instance Profile / OIDC Web Identity
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
