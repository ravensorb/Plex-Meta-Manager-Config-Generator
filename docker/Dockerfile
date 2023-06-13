# syntax=docker/dockerfile:1

FROM python:3.10-slim-bullseye

# arguments
ARG BRANCH_NAME=master
ARG BUILD_DATE
ARG VERSION

# set version label
LABEL build_version="LiquidLogicLabs version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="ravensorb"

# environment settings
ENV BRANCH_NAME ${BRANCH_NAME}
ENV TINI_VERSION v0.19.0
ENV HOME="/config" \
  PYTHONIOENCODING=utf-8

# add local files
COPY root/ /

RUN echo "**** install system packages ****" \
 && apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && apt-get install -y tzdata --no-install-recommends \
 && apt-get install -y gcc g++ libxml2-dev libxslt-dev libz-dev libjpeg62-turbo-dev zlib1g-dev wget curl \
 && wget -O /tini https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini-"$(dpkg --print-architecture | awk -F- '{ print $NF }')" \
 && chmod +x /tini \
 && pip3 install --no-cache-dir --upgrade pmm-cfg-gen \
 && apt-get --purge autoremove gcc g++ libxml2-dev libxslt-dev libz-dev -y \
 && apt-get clean \
 && apt-get update \
 && apt-get check \
 && apt-get -f install \
 && apt-get autoclean \
 && rm -rf /tmp/* /var/tmp/* /var/lib/apt/lists/*

# volumes
VOLUME [ "/config", "/data", "/pmm_config" ]

WORKDIR /config

# Entrypoint
ENTRYPOINT ["/tini", "-s", "python3", "-m", "pmm-cfg-gen", "--"]

