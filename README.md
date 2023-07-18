# Plex-Meta-Manager-Config-Generator

[![PyPI version](https://badge.fury.io/py/pmm-cfg-gen.svg)](https://badge.fury.io/py/pmm-cfg-gen)

A python application to automatically generate Plex Meta Manager configuration files based on your plex libraries.

Library types supported:

* Movie
* TV
* Music (json format only)

## Install

```shell
pip install pmm-cfg-gen
```

## Running from command line

Usage:

```shell
usage: pmm-cfg-gen [-h] [--plex.serverUrl PLEX.SERVERURL] [--plex.token PLEX.TOKEN] [--plex.lbraries [PLEX.LBRARIES ...]] [--output.path OUTPUT.PATH] [--output.overwrite OUTPUT.OVERWRITE]
                   [--theMovieDatabase.apiKey THEMOVIEDATABASE.APIKEY] [--thePosterDatabase.enablePro] [--pmm.deltaOnly] [--logLevel {INFO,WARN,DEBUG,CRITICAL}]

options:
  -h, --help            show this help message and exit
  --plex.serverUrl PLEX.SERVERURL
                        Plex Server fully qualifed URL
  --plex.token PLEX.TOKEN
                        Authentication Token (not claim token) for the plex server
  --plex.lbraries [PLEX.LBRARIES ...]
                        Comma delimited list of libraries to process
  --output.path OUTPUT.PATH
                        Root path to store generated files (default: ./data)
  --output.overwrite OUTPUT.OVERWRITE
                        Overwrite existing files (default: False)
  --theMovieDatabase.apiKey THEMOVIEDATABASE.APIKEY
                        The Movie Database API Key
  --thePosterDatabase.enablePro
                        Enable Pro features for The Poster Database (requires you to be able to login to the site)
  --pmm.deltaOnly       Only generate files for items that do not already exist in current PMM configs
  --logLevel {INFO,WARN,DEBUG,CRITICAL}
                        Logging Level (default: INFO)

```

## Configuration File

All of the configuration can be stored in a ```config.yaml``` file that uses the following format (with the exception of logLevel).

config.yaml:

```yaml
plex:
  serverUrl: <plex server url>
  token: <plex token>
  libraries:
    - { name: "TV Shows", path: "tv", pmm_path: "/pmm_config/tv" }
    - { name: "Movies", path: "movies" }

plexMetaManager:
  cacheExistingFiles: true

theMovieDatabase:
  apiKey: <tmdb api key>

output:
    path: <path to store generated output>
```

Notes:

* It is possible to use ENV variables (standard bash syntax supported).
* If The Movia Database API Key is set, collection details are looked up realtime

Example:

```yaml
plex:
    serverUrl: ${PLEX_SERVER:-https://plex:32400}
    token: ${PLEX_TOKEN}
```
