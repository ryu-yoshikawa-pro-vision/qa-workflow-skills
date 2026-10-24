FROM node:24.21.0-bookworm-slim

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        bash git python3.11 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN npm install --global @openai/codex@0.163.0 \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python \
    && test "$(codex --version)" = "codex-cli 0.163.0" \
    && test -s /etc/ssl/certs/ca-certificates.crt \
    && python3.11 --version

WORKDIR /workspace
