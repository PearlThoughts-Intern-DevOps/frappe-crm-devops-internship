variable "aws_region" {
  description = "AWS region where infrastructure will be configured"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Name of the Terraform project"
  type        = string
  default     = "terraform-aws-demo"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "allowed_ssh_cidr" {
  description = "IP range allowed to connect through SSH"
  type        = string
  default     = "203.0.113.10/32"
}
