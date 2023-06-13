# Plex-Meta-Manager-Config-Generator

Created by: Shawn Anderson

## Overview

This docker container provides a method for running the pmm-cfg-gen application locally in an isolated and self-contained environment.

pmm-cfg-gen is a tool that simplifes the creation of Plex-Meta-Manager configuration files (collection and metadata for movie and tv libraries).

## Container: pmm-cfg-gen

* Image: pmm-cfg-gen
* Link: ravensorb/pmm-cfg-gen

### Environment Variables

|Name|Value|Comment|
|---|---|---|
|PLEX_URL|https://plex:32400|Define the plex server url (including port)|
|PLEX_TOKEN|xxxxxxxxxxxxxxxx|Optional. Define the plex token (auth token -- NOT claim token)|
|TMDB_API_KEY|xxxxxxxxxxxxxxxx|Optional. Define the movie database api key|

## Usage

### docker

```shell
docker run -name pmm-cfg-gen --rm \
                             -e PLEX_URL=https://plex:32400
                             -e PLEX_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxx
                             -e TMDB_API_TOKEN=xxxxxxxxxxxxxxxxxxxxxx
                             -v ./config:/config
                             -v ./pmm_config:/pmm_config
                             -ti ravensorb/pmm-cfg-gen:latest
```

### Docker-Compose:

**Sample:** docker-compose.yml

```docker-compose
---
version: "3.1"

services:
  pmm-cfg-gen:
    build:
      context: .
      dockerfile: Dockerfile
    image: ravensorb/pmm-cfg-gen:latest
    container_name: pmm-cfg-gen
    environment:
      - PLEX_URL=https://plex:32400
      - PLEX_TOKEN=xxxxxxxxxxxxxxxxxxxx
      - TMDB_API_KEY=xxxxxxxxxxxxxxxxxxxx
    volumes:
      - ./config:/config
      - ./pmm_config:/pmm_config
    logging:
      driver: json-file
      options:
        max-size: "100m"
        max-file: "10"
    security_opt:
      - no-new-privileges:true
```

Shell command:

```shell
docker-compose up -d
```