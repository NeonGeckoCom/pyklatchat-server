FROM python:3.12-slim-bookworm

LABEL vendor=neon.ai \
    ai.neon.name="pyklatchat-server"

ENV OVOS_CONFIG_BASE_FOLDER=neon
ENV OVOS_CONFIG_FILENAME=klat.yaml
ENV XDG_CONFIG_HOME=/config
ENV KLAT_ENV=PROD

COPY . /app/

WORKDIR /app

RUN apt-get update \
    && apt-get install build-essential git -y \
    && pip install --no-cache-dir --upgrade pip wheel

RUN pip install --no-cache-dir /app


CMD ["pyklatchat-server"]
