FROM frappe/bench:latest

USER frappe
WORKDIR /home/frappe

RUN bench init frappe-bench --frappe-branch version-15 --skip-redis-config-generation

WORKDIR /home/frappe/frappe-bench

RUN bench get-app crm --branch main https://github.com/frappe/crm
RUN sed -i '/^redis/d;/^watch/d' Procfile

WORKDIR /home/frappe

COPY --chown=frappe:frappe docker/entrypoint.sh .
COPY --chown=frappe:frappe healthcheck.sh .

RUN chmod +x entrypoint.sh healthcheck.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=5 \
    CMD /home/frappe/healthcheck.sh

CMD ["/home/frappe/entrypoint.sh"]