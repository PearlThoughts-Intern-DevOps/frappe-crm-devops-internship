#!/bin/bash
set -eo pipefail

# =============================================================================
# Helper Script: Build and Push Frappe CRM Image to AWS ECR
# =============================================================================

AWS_REGION="${AWS_REGION:-ap-southeast-2}"
ECR_REPO_NAME="${ECR_REPO_NAME:-frappe-crm}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')}"

echo "================================================================="
echo "   Frappe CRM ECR Build & Push Tool                              "
echo "================================================================="
echo "Region:     ${AWS_REGION}"
echo "Repository: ${ECR_REPO_NAME}"
echo "Image Tag:  ${IMAGE_TAG}"
echo "================================================================="

# Retrieve AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPO_NAME}:${IMAGE_TAG}"
LATEST_URI="${ECR_REGISTRY}/${ECR_REPO_NAME}:latest"

echo "[1/4] Authenticating with Amazon ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

echo "[2/4] Verifying ECR repository '${ECR_REPO_NAME}' exists..."
aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${AWS_REGION}" >/dev/null 2>&1 || {
    echo "[INFO] Creating ECR repository '${ECR_REPO_NAME}'..."
    aws ecr create-repository \
        --repository-name "${ECR_REPO_NAME}" \
        --image-scanning-configuration scanOnPush=true \
        --region "${AWS_REGION}"
}

echo "[3/4] Building production Docker image for linux/amd64 (Fargate target)..."
docker build \
    --platform linux/amd64 \
    --file docker/Dockerfile \
    --tag "${IMAGE_URI}" \
    --tag "${LATEST_URI}" \
    .

echo "[4/4] Pushing images to Amazon ECR..."
docker push "${IMAGE_URI}"
docker push "${LATEST_URI}"

echo "================================================================="
echo "[SUCCESS] Image successfully pushed to ECR!"
echo "Image URI:  ${IMAGE_URI}"
echo "Latest URI: ${LATEST_URI}"
echo "================================================================="
