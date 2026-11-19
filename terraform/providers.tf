terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Credentials are NOT set here. Terraform reads them from your environment
# (aws configure / AWS_ACCESS_KEY_ID / AWS_PROFILE), never from the code.
provider "aws" {
  region = var.aws_region
}
