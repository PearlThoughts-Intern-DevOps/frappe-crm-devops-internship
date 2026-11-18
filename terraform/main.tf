resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.subnet_cidr
  map_public_ip_on_launch = false

  tags = {
    Name = "${var.project_name}-subnet"
  }
}

resource "aws_security_group" "main" {
  name        = "${var.project_name}-sg"
  description = "Security group for Terraform assignment"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-sg"
  }
}


resource "aws_s3_bucket" "storage" {
  bucket_prefix = "${var.project_name}-storage-"

  tags = {
    Name        = "${var.project_name}-bucket"
    Environment = "development"
  }
}