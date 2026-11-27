# Script to deploy the updated Frappe CRM configuration to the AWS EC2 instance
param (
    [string]$ServerIP = "13.204.77.123",
    [string]$KeyPath = "$HOME\.ssh\frappe_ec2_key"
)

Write-Host "==> 1. Uploading updated init.sh, docker-compose.yml, and .env to EC2 ($ServerIP)..." -ForegroundColor Cyan
scp -i $KeyPath -o StrictHostKeyChecking=no "$PSScriptRoot\init.sh" "ec2-user@${ServerIP}:/home/ec2-user/init.sh"
scp -i $KeyPath -o StrictHostKeyChecking=no "$PSScriptRoot\docker-compose.yml" "ec2-user@${ServerIP}:/home/ec2-user/docker-compose.yml"
scp -i $KeyPath -o StrictHostKeyChecking=no "$PSScriptRoot\.env" "ec2-user@${ServerIP}:/home/ec2-user/.env"

Write-Host "==> 2. Resetting and launching fresh Frappe CRM containers on EC2..." -ForegroundColor Cyan
ssh -i $KeyPath -o StrictHostKeyChecking=no "ec2-user@$ServerIP" "sed -i 's/\r$//' /home/ec2-user/init.sh && chmod +x /home/ec2-user/init.sh && sudo docker compose down -v && sudo docker compose up -d"

Write-Host "==> 3. Streaming installation logs (this will install CRM and build the site)..." -ForegroundColor Green
Write-Host "Press Ctrl+C at any time to exit log streaming (the installation will continue on the server)." -ForegroundColor Yellow
ssh -i $KeyPath -o StrictHostKeyChecking=no "ec2-user@$ServerIP" "sudo docker logs -f crm-frappe-1"
