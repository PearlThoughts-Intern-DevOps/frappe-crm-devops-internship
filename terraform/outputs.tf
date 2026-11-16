# =============================================================================
# OUTPUTS
# =============================================================================

# Networking Outputs
output "vpc_id" {
  description = "The ID of the provisioned VPC."
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "The ID of the public subnet."
  value       = aws_subnet.public.id
}

# Security Outputs
output "security_group_id" {
  description = "The ID of the web security group."
  value       = aws_security_group.web.id
}

# Compute Outputs
output "ec2_instance_id" {
  description = "The ID of the EC2 instance."
  value       = aws_instance.web.id
}

output "ec2_public_ip" {
  description = "Public IPv4 address of the EC2 instance."
  value       = aws_instance.web.public_ip
}

output "ec2_private_ip" {
  description = "Private IPv4 address of the EC2 instance."
  value       = aws_instance.web.private_ip
}

# Storage Outputs
output "s3_bucket_name" {
  description = "The name of the created S3 bucket."
  value       = aws_s3_bucket.app_storage.id
}

output "s3_bucket_arn" {
  description = "The ARN of the created S3 bucket."
  value       = aws_s3_bucket.app_storage.arn
}

# Region Output
output "aws_region" {
  description = "AWS Region where resources are defined."
  value       = var.aws_region
}
