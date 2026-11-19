
output "vpc_id" {
  description = "Created VPC ID"
  value       = aws_vpc.web_vpc.id
}

output "subnet_id" {
  description = "Created subnet ID"
  value       = aws_subnet.web_subnet.id
}

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.web_server.id
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.web_sg.id
}
