FROM frappe/bench:latest AS base

LABEL maintainer="Gourob Das <gourobdas0103>"
LABEL description="Production Frappe CRM Container for AWS ECS Fargate Blue-Green Deployment"
LABEL org.opencontainers.image.source="https://github.com/PearlThoughts-Intern-DevOps/frappe-crm-devops-internship"

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    mariadb-client \
    netcat-openbsd \
    jq \
    && rm -rf /var/lib/apt/lists/*

USER frappe
WORKDIR /home/frappe

# Initialize frappe-bench v15
RUN bench init --ignore-exist --skip-redis-config-generation --version version-15 frappe-bench

WORKDIR /home/frappe/frappe-bench

# Remove local redis / watch from Procfile
RUN sed -i '/redis/d' ./Procfile && \
    sed -i '/watch/d' ./Procfile

# Copy CRM application source and build definitions
COPY --chown=frappe:frappe package.json /home/frappe/frappe-bench/apps/crm/package.json
COPY --chown=frappe:frappe yarn.lock /home/frappe/frappe-bench/apps/crm/yarn.lock
COPY --chown=frappe:frappe pyproject.toml /home/frappe/frappe-bench/apps/crm/pyproject.toml
COPY --chown=frappe:frappe README.md /home/frappe/frappe-bench/apps/crm/README.md
COPY --chown=frappe:frappe crm /home/frappe/frappe-bench/apps/crm/crm
COPY --chown=frappe:frappe frappe-ui /home/frappe/frappe-bench/apps/crm/frappe-ui
COPY --chown=frappe:frappe frontend /home/frappe/frappe-bench/apps/crm/frontend

# Install Python package in editable mode and register in apps.txt
RUN ./env/bin/pip install --no-cache-dir -e apps/crm && \
    grep -qxF 'crm' sites/apps.txt 2>/dev/null || echo 'crm' >> sites/apps.txt

# Compile Vue 3 / Vite frontend assets to produce crm/www/crm.html and public assets
RUN cd apps/crm/frontend && \
    yarn install --frozen-lockfile || yarn install && \
    yarn build && \
    cd /home/frappe/frappe-bench

# Ensure Python can resolve frappecrm alias to crm
RUN ./env/bin/python -c "import site, os; os.symlink('/home/frappe/frappe-bench/apps/crm/crm', os.path.join(site.getsitepackages()[0], 'frappecrm'))" 2>/dev/null || true

# Copy entrypoint script
COPY --chown=frappe:frappe docker/entrypoint.sh /home/frappe/entrypoint.sh
RUN chmod +x /home/frappe/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/api/method/frappe.ping || exit 1

ENTRYPOINT ["/home/frappe/entrypoint.sh"]
