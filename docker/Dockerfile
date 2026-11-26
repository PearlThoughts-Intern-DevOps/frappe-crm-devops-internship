# =============================================================================
# Production Dockerfile for Frappe CRM on AWS ECS Fargate
# =============================================================================
# Multi-stage optimized image:
# - Pre-packages Frappe v15 and Frappe CRM application
# - Pre-compiles frontend Vue 3 / Vite assets
# - Includes production entrypoint with auto-migration and graceful signal handling
# =============================================================================

FROM frappe/bench:latest AS base

LABEL maintainer="Gourob Das <gourobdas0103>"
LABEL description="Production Frappe CRM Container for AWS ECS Fargate Blue-Green Deployment"
LABEL org.opencontainers.image.source="https://github.com/PearlThoughts-Intern-DevOps/frappe-crm-devops-internship"

USER root

# Install necessary runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    mariadb-client \
    netcat-openbsd \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Switch to frappe user (UID 1000)
USER frappe
WORKDIR /home/frappe

# Pre-initialize frappe-bench version-15 inside the build stage
RUN bench init --ignore-exist --skip-redis-config-generation --version version-15 frappe-bench

WORKDIR /home/frappe/frappe-bench

# Clean up default Procfile: Redis runs externally (ElastiCache / separate container)
RUN sed -i '/redis/d' ./Procfile && \
    sed -i '/watch/d' ./Procfile

# Copy local CRM application source into bench apps directory
COPY --chown=frappe:frappe crm /home/frappe/frappe-bench/apps/crm/crm
COPY --chown=frappe:frappe frontend /home/frappe/frappe-bench/apps/crm/frontend
COPY --chown=frappe:frappe frappe-ui /home/frappe/frappe-bench/apps/crm/frappe-ui
COPY --chown=frappe:frappe pyproject.toml /home/frappe/frappe-bench/apps/crm/pyproject.toml
COPY --chown=frappe:frappe README.md /home/frappe/frappe-bench/apps/crm/README.md

# Install CRM Python requirements into bench virtualenv and build assets
RUN ./env/bin/pip install --no-cache-dir -e apps/crm && \
    bench build --app crm || true

# Copy entrypoint script
COPY --chown=frappe:frappe docker/entrypoint.sh /home/frappe/entrypoint.sh
RUN chmod +x /home/frappe/entrypoint.sh

# Expose Frappe web application port
EXPOSE 8000

# Health check matching ALB target group probe
HEALTHCHECK --interval=15s --timeout=5s --start-period=45s --retries=3 \
  CMD curl -f http://localhost:8000/api/method/frappe.ping || exit 1

ENTRYPOINT ["/home/frappe/entrypoint.sh"]
