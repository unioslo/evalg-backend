FROM harbor.uio.no/library/docker.io-python:3.9-slim

LABEL no.uio.contact=bnt-int@usit.uio.no

# Proxy for updates during build
ENV http_proxy="http://software-proxy.uio.no:3128"
ENV https_proxy="http://software-proxy.uio.no:3128"
ENV no_proxy="bitbucket.usit.uio.no"

RUN apt-get update && apt-get install -y \
    git \
    libpq-dev \
    gcc \
    python3-psycopg2 \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=falsei \
    EVALG_CONFIG="/usr/local/var/evalg-instance/evalg_config.py" \
    FLASK_APP="evalg.wsgi"


RUN pip3 install poetry

RUN mkdir /evalg
WORKDIR /evalg
COPY . /evalg

# Build and install evalg
RUN poetry build -f wheel
RUN pip3 install dist/evalg-*.whl

# Remove proxy_settings
ENV http_proxy=""
ENV https_proxy=""

# Support arbitrarily assigned UIDs by making the root group
# # the owner of our directory.
RUN chgrp -R 0 /evalg && \
    chmod -R g=u /evalg
