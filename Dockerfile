FROM debian:13.4

RUN apt-get update
RUN apt-get install -y nodejs npm python3 python3-pip ripgrep ffmpeg gcc python3-dev libffi-dev

COPY . /opt/hermes
WORKDIR /opt/hermes

RUN pip install -e ".[all]" --break-system-packages
RUN npm install
RUN npx playwright install --with-deps chromium
WORKDIR /opt/hermes/scripts/whatsapp-bridge
RUN npm install

WORKDIR /opt/hermes
RUN chmod +x /opt/hermes/docker/entrypoint.sh

ENV HERMES_HOME=/opt/data
# Persist data by mounting a volume at /opt/data (e.g. Railway project volume — do not use Dockerfile VOLUME; Railway forbids it).
# Default: run the messaging gateway (Telegram/Discord/Slack/…). Override for local shells, e.g. `docker run … hermes chat`.
ENTRYPOINT [ "/opt/hermes/docker/entrypoint.sh" ]
CMD [ "gateway", "run" ]