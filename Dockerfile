FROM frappe/bench:latest

USER frappe
WORKDIR /home/frappe


ARG FRAPPE_BRANCH=version-15
ARG CRM_BRANCH=main

RUN bench init frappe-bench --frappe-branch ${FRAPPE_BRANCH} --skip-redis-config-generation \
 && cd frappe-bench \
 && bench get-app crm --branch ${CRM_BRANCH} https://github.com/frappe/crm \
 && sed -i '/^redis/d;/^watch/d' Procfile

COPY --chown=frappe:frappe docker/entrypoint.sh /home/frappe/entrypoint.sh
COPY --chown=frappe:frappe healthcheck.sh /home/frappe/healthcheck.sh
RUN chmod +x /home/frappe/entrypoint.sh /home/frappe/healthcheck.sh

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=5 \
  CMD /home/frappe/healthcheck.sh

CMD ["/home/frappe/entrypoint.sh"]
