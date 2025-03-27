FROM python:3.12-slim-bookworm

ENV OVOS_CONFIG_BASE_FOLDER=neon
ENV OVOS_CONFIG_FILENAME=klat.yaml
ENV XDG_CONFIG_HOME=/config
ENV KLAT_ENV=PROD

COPY . /app/

WORKDIR /app

RUN apt-get update \
    && apt-get install -y \
    && apt install build-essential -y \
    && pip install --upgrade pip  \
    && pip install wheel

RUN pip install /app


CMD ["pyklatchat-server"]
