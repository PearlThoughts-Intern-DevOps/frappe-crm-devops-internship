@echo off
set SERVER_IP=13.204.77.123
set KEY_PATH=%USERPROFILE%\.ssh\frappe_ec2_key

echo ==> 1. Uploading updated init.sh, docker-compose.yml, and .env to EC2 (%SERVER_IP%)...
scp -i %KEY_PATH% -o StrictHostKeyChecking=no init.sh ec2-user@%SERVER_IP%:/home/ec2-user/init.sh
scp -i %KEY_PATH% -o StrictHostKeyChecking=no docker-compose.yml ec2-user@%SERVER_IP%:/home/ec2-user/docker-compose.yml
scp -i %KEY_PATH% -o StrictHostKeyChecking=no .env ec2-user@%SERVER_IP%:/home/ec2-user/.env

echo ==> 2. Resetting containers on EC2...
ssh -i %KEY_PATH% -o StrictHostKeyChecking=no ec2-user@%SERVER_IP% "sed -i 's/\r$//' /home/ec2-user/init.sh && chmod +x /home/ec2-user/init.sh && sudo docker compose down -v && sudo docker compose up -d"

echo ==> 3. Streaming live installation logs...
echo (Press Ctrl+C at any time to disconnect)
ssh -i %KEY_PATH% -o StrictHostKeyChecking=no ec2-user@%SERVER_IP% "sudo docker logs -f crm-frappe-1"
