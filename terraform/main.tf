# =============================================================================
# DATA SOURCES
# =============================================================================

# Fetch the latest official Ubuntu 24.04 LTS (Noble Numbat) AMI from Canonical
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical official AWS account ID

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# =============================================================================
# 1. NETWORKING: Amazon Virtual Private Cloud (VPC) & Subnet
# =============================================================================

# Dedicated VPC with DNS hostnames and resolution enabled
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-${var.environment}-vpc"
  }
}

# Internet Gateway to provide outbound/inbound internet connectivity
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-${var.environment}-igw"
  }
}

# Public Subnet in the specified Availability Zone
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-${var.environment}-public-subnet"
    Type = "Public"
  }
}

# Route Table directing all outbound traffic to the Internet Gateway
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-public-rt"
  }
}

# Associate Public Subnet with the Public Route Table
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# =============================================================================
# 2. SECURITY: AWS Security Group (Firewall)
# =============================================================================

resource "aws_security_group" "web" {
  name        = "${var.project_name}-${var.environment}-web-sg"
  description = "Security group for web server with SSH, HTTP, and HTTPS access"
  vpc_id      = aws_vpc.main.id

  # Inbound HTTP (Port 80)
  ingress {
    description = "Allow inbound HTTP traffic"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_http_cidrs
  }

  # Inbound HTTPS (Port 443)
  ingress {
    description = "Allow inbound HTTPS traffic"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_https_cidrs
  }

  # Inbound SSH (Port 22)
  ingress {
    description = "Allow inbound SSH access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  # Outbound Egress - Allow all outgoing traffic (updates, packages, external APIs)
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-web-sg"
  }
}

# =============================================================================
# 3. COMPUTE: Amazon EC2 Instance
# =============================================================================

resource "aws_instance" "web" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.web.id]
  associate_public_ip_address = true

  # Security Best Practice: Enforce IMDSv2 to protect against SSRF credential theft
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2 required
    http_put_response_hop_limit = 1
  }

  # Security & Storage: Encrypted EBS root volume
  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    encrypted             = true
    delete_on_termination = true

    tags = {
      Name = "${var.project_name}-${var.environment}-root-volume"
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-web-server"
    Role = "ApplicationServer"
  }
}

# =============================================================================
# 4. STORAGE: Amazon S3 (Simple Storage Service) Bucket
# =============================================================================

# S3 Bucket with automated unique name suffix
resource "aws_s3_bucket" "app_storage" {
  bucket_prefix = "${var.bucket_name_prefix}-${var.environment}-"

  tags = {
    Name    = "${var.project_name}-${var.environment}-storage"
    Purpose = "Application Assets and Backups"
  }
}

# Reliability Best Practice: Bucket Versioning to protect against accidental deletes/overwrites
resource "aws_s3_bucket_versioning" "app_storage_versioning" {
  bucket = aws_s3_bucket.app_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Security Best Practice: Default Server-Side Encryption (SSE-S3 / AES256)
resource "aws_s3_bucket_server_side_encryption_configuration" "app_storage_encryption" {
  bucket = aws_s3_bucket.app_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Security Best Practice: Block all public access at the bucket level
resource "aws_s3_bucket_public_access_block" "app_storage_public_access_block" {
  bucket = aws_s3_bucket.app_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
