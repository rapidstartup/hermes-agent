FROM debian:13.4

# Disable Python stdout buffering to ensure logs are printed immediately
ENV PYTHONUNBUFFERED=1
# Debian PEP 668 + Hermes on system Python: allow uv to install into dist-packages
ENV UV_BREAK_SYSTEM_PACKAGES=1

# Install system dependencies in one layer, clear APT cache
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential nodejs npm python3 python3-pip ripgrep ffmpeg gcc python3-dev libffi-dev ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# uv's resolver handles the large [all] extra graph; pip on Py3.13 often hits resolution-too-deep
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /usr/local/bin/

COPY . /opt/hermes
WORKDIR /opt/hermes

# Install Python and Node dependencies in one layer, no cache
RUN uv pip install --system --no-cache -e ".[all]" && \
    npm install --prefer-offline --no-audit && \
    npx playwright install --with-deps chromium --only-shell && \
    cd /opt/hermes/scripts/whatsapp-bridge && \
    npm install --prefer-offline --no-audit && \
    npm cache clean --force

WORKDIR /opt/hermes
RUN chmod +x /opt/hermes/docker/entrypoint.sh

ENV HERMES_HOME=/opt/data
# Persist data by mounting a volume at /opt/data (e.g. Railway project volume — do not use Dockerfile VOLUME; Railway forbids it).
# Default: run the messaging gateway (Telegram/Discord/Slack/…). Override for local shells, e.g. `docker run … hermes chat`.
ENTRYPOINT [ "/opt/hermes/docker/entrypoint.sh" ]
CMD [ "gateway", "run" ]
