FROM postgres:18-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends awscli ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY backup.sh /usr/local/bin/backup.sh

USER postgres
ENTRYPOINT ["/bin/sh", "/usr/local/bin/backup.sh"]
