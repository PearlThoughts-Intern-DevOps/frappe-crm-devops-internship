# -----------------------------------------------------------------------------
# General Project Variables
# -----------------------------------------------------------------------------

variable "aws_region" {
  description = "Target AWS Region for infrastructure deployment."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project used for resource naming and tagging."
  type        = string
  default     = "frappe-crm"
}

variable "environment" {
  description = "Deployment environment (e.g., dev, staging, prod)."
  type        = string
  default     = "dev"
}

# -----------------------------------------------------------------------------
# Networking Variables (VPC & Subnet)
# -----------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "IPv4 CIDR block for the custom VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "IPv4 CIDR block for the public subnet."
  type        = string
  default     = "10.0.1.0/24"
}

variable "availability_zone" {
  description = "Target Availability Zone for the public subnet."
  type        = string
  default     = "us-east-1a"
}

# -----------------------------------------------------------------------------
# Security Group Variables
# -----------------------------------------------------------------------------

variable "allowed_ssh_cidrs" {
  description = "Allowed IPv4 CIDR blocks for incoming SSH access on port 22."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allowed_http_cidrs" {
  description = "Allowed IPv4 CIDR blocks for incoming HTTP access on port 80."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allowed_https_cidrs" {
  description = "Allowed IPv4 CIDR blocks for incoming HTTPS access on port 443."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# -----------------------------------------------------------------------------
# Compute Variables (EC2)
# -----------------------------------------------------------------------------

variable "instance_type" {
  description = "EC2 instance size/type for the application server."
  type        = string
  default     = "t3.micro"
}

variable "root_volume_size" {
  description = "Size of the root EBS volume in Gigabytes (GiB)."
  type        = number
  default     = 20
}

# -----------------------------------------------------------------------------
# Storage Variables (S3)
# -----------------------------------------------------------------------------

variable "bucket_name_prefix" {
  description = "Prefix for the S3 bucket name. Must be globally unique and lowercase."
  type        = string
  default     = "frappe-crm-app-storage"
}
