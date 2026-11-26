output "ec2_instance_id" {
  description = "EC2 Instance ID"
  value       = aws_instance.frappe_obs.id
}

output "ec2_public_ip" {
  description = "EC2 Public IPv4 Address"
  value       = aws_instance.frappe_obs.public_ip
}

output "frappe_crm_url" {
  description = "Frappe CRM Web UI URL"
  value       = "http://${aws_instance.frappe_obs.public_ip}/crm"
}

output "grafana_url" {
  description = "Grafana Observability UI URL"
  value       = "http://${aws_instance.frappe_obs.public_ip}:3000"
}

output "prometheus_url" {
  description = "Prometheus UI URL"
  value       = "http://${aws_instance.frappe_obs.public_ip}:9090"
}

output "ssm_connect_command" {
  description = "Command to connect without SSH keys using AWS SSM Session Manager"
  value       = "aws ssm start-session --target ${aws_instance.frappe_obs.id} --region ${var.aws_region}"
}
