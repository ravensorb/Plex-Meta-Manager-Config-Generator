# Plex-Meta-Manager-Config-Generator

[![PyPI version](https://badge.fury.io/py/pmm-cfg-gen.svg)](https://badge.fury.io/py/pmm-cfg-gen)

A python script to automatically generate Plex Meta Manager configuration files based on your plex libraries.

## Install

```shell
pip install pmm-cfg-gen
```

## Running from command line

Usage:

```shell
usage: pmm-cfg-gen [-h] [--plex.serverUrl PLEX.SERVERURL] [--plex.token PLEX.TOKEN] [--plex.lbraries [PLEX.LBRARIES ...]] [--output.path OUTPUT.PATH] [--logLevel {INFO,WARN,DEBUG,CRITICAL}]

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
  --logLevel {INFO,WARN,DEBUG,CRITICAL}
                        Logging Level (default: INFO)

```

## Configuration File

All of the configuration can be stored in a ```config.yaml``` file that uses the following format (with the exception of logLevel).

config.yaml:

```yaml
plex:
  serverUrl: <plex server>
  token: <plex token>
  libraries:
    - <plex library name>
    - <plex library name>
    - <plex library name>
    
theMovieDatabase:
  apiKey: <api key for tmdb>

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
