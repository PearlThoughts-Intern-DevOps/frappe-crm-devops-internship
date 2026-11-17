output "vpc_id" {
  description = "ID of the created VPC"
  value       = aws_vpc.main.id
}

output "subnet_id" {
  description = "ID of the created subnet"
  value       = aws_subnet.private.id
}

output "security_group_id" {
  description = "ID of the created security group"
  value       = aws_security_group.web.id
}

output "ec2_instance_id" {
  description = "ID of the created EC2 instance"
  value       = aws_instance.web.id
}

output "ec2_private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.web.private_ip
}
