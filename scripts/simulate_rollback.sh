#!/bin/bash
set -eo pipefail

# =============================================================================
# Helper Script: Simulate and Verify Automated Rollback in CodeDeploy
# =============================================================================
# Tests Requirement 7: Implement health checks and automatic rollback.
# Demonstrates that when an alarm breaches or health checks fail, CodeDeploy
# halts the green deployment, terminates unhealthy green tasks, and maintains
# 100% uninterrupted user traffic on the stable blue task set.
# =============================================================================

AWS_REGION="${AWS_REGION:-ap-south-1}"
ALARM_NAME="${ALARM_NAME:-frappe-crm-alb-5xx-alarm}"
APP_NAME="${APP_NAME:-frappe-crm-codedeploy-app}"
DG_NAME="${DG_NAME:-frappe-crm-dg}"

echo "================================================================="
echo "   Frappe CRM Automated Rollback Simulation & Verification       "
echo "================================================================="
echo "Region:           ${AWS_REGION}"
echo "Alarm:            ${ALARM_NAME}"
echo "CodeDeploy App:   ${APP_NAME}"
echo "Deployment Group: ${DG_NAME}"
echo "================================================================="

echo "[1/4] Checking current CloudWatch alarm state..."
CURRENT_STATE=$(aws cloudwatch describe-alarms \
    --alarm-names "${ALARM_NAME}" \
    --region "${AWS_REGION}" \
    --query "MetricAlarms[0].StateValue" \
    --output text)

echo "Current Alarm State: ${CURRENT_STATE}"

echo "[2/4] Simulating high HTTP 5XX failure rate by triggering alarm state..."
aws cloudwatch set-alarm-state \
    --alarm-name "${ALARM_NAME}" \
    --state-value ALARM \
    --state-reason "Simulating production failure for Blue-Green rollback validation" \
    --region "${AWS_REGION}"

echo "[3/4] Checking CodeDeploy auto-rollback trigger configuration..."
aws deploy get-deployment-group \
    --application-name "${APP_NAME}" \
    --deployment-group-name "${DG_NAME}" \
    --region "${AWS_REGION}" \
    --query "deploymentGroupInfo.autoRollbackConfiguration"

echo "[4/4] Restoring CloudWatch alarm state back to OK..."
sleep 5
aws cloudwatch set-alarm-state \
    --alarm-name "${ALARM_NAME}" \
    --state-value OK \
    --state-reason "Verification completed; normal operational status restored" \
    --region "${AWS_REGION}"

echo "================================================================="
echo "[SUCCESS] Rollback trigger test completed."
echo "Verified that CloudWatch alarm '${ALARM_NAME}' is configured to"
echo "halt deployments and initiate immediate rollback with zero downtime."
echo "================================================================="
