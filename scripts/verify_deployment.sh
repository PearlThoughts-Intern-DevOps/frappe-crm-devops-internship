#!/bin/bash
set -eo pipefail

# =============================================================================
# Helper Script: Verify Frappe CRM ECS Blue-Green Deployment & Health Status
# =============================================================================

AWS_REGION="${AWS_REGION:-ap-south-1}"
CLUSTER_NAME="${CLUSTER_NAME:-frappe-crm-cluster}"
SERVICE_NAME="${SERVICE_NAME:-frappe-crm-service}"
LOG_GROUP="/ecs/frappe-crm"

echo "================================================================="
echo "   Frappe CRM ECS Deployment Verification Tool                   "
echo "================================================================="

echo "[1/4] Inspecting ECS Fargate Service Status..."
aws ecs describe-services \
    --cluster "${CLUSTER_NAME}" \
    --services "${SERVICE_NAME}" \
    --region "${AWS_REGION}" \
    --query "services[0].{Status:status,Desired:desiredCount,Running:runningCount,Pending:pendingCount,TaskDefinition:taskDefinition}" \
    --output table || true

echo "[2/4] Inspecting ALB Target Group Health (Blue & Green)..."
TARGET_GROUPS=$(aws elbv2 describe-target-groups \
    --names frappe-crm-tg-blue frappe-crm-tg-green \
    --region "${AWS_REGION}" \
    --query "TargetGroups[*].TargetGroupArn" \
    --output text 2>/dev/null || true)

for TG_ARN in ${TARGET_GROUPS}; do
    TG_NAME=$(aws elbv2 describe-target-groups --target-group-arns "${TG_ARN}" --region "${AWS_REGION}" --query "TargetGroups[0].TargetGroupName" --output text)
    echo "--- Target Group: ${TG_NAME} ---"
    aws elbv2 describe-target-health \
        --target-group-arn "${TG_ARN}" \
        --region "${AWS_REGION}" \
        --query "TargetHealthDescriptions[*].{Id:Target.Id,Port:Target.Port,Health:TargetHealth.State,Reason:TargetHealth.Reason}" \
        --output table || true
done

echo "[3/4] Testing Application Health Probes via ALB..."
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names frappe-crm-alb \
    --region "${AWS_REGION}" \
    --query "LoadBalancers[0].DNSName" \
    --output text 2>/dev/null || true)

if [ -n "${ALB_DNS}" ]; then
    echo "Production URL (Port 80): http://${ALB_DNS}/api/method/frappe.ping"
    curl -I -s --max-time 5 "http://${ALB_DNS}/api/method/frappe.ping" || echo "[WARN] ALB not reachable yet."

    echo "Test URL (Port 8080): http://${ALB_DNS}:8080/api/method/frappe.ping"
    curl -I -s --max-time 5 "http://${ALB_DNS}:8080/api/method/frappe.ping" || echo "[WARN] Test listener not reachable or inactive."
else
    echo "[INFO] ALB DNS name not found or not provisioned yet."
fi

echo "[4/4] Fetching latest CloudWatch logs from ${LOG_GROUP}..."
aws logs filter-log-events \
    --log-group-name "${LOG_GROUP}" \
    --limit 10 \
    --region "${AWS_REGION}" \
    --query "events[*].{Timestamp:timestamp,Message:message}" \
    --output table 2>/dev/null || echo "[INFO] No log events recorded yet."

echo "================================================================="
echo "[SUCCESS] Deployment verification completed."
echo "================================================================="
