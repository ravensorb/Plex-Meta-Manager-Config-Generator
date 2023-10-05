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
sage: pmm-cfg-gen [-h] [--plex.serverUrl PLEX.SERVERURL] [--plex.token PLEX.TOKEN] [--plex.lbraries [PLEX.LBRARIES ...]] [--output.path OUTPUT.PATH] [--output.overwrite OUTPUT.OVERWRITE]
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
  --pmm.deltaOnly       Only generate files for items that do not already exist
  --logLevel {INFO,WARN,DEBUG,CRITICAL}
                        Logging Level (default: INFO)
```

## Configuration File

All of the configuration can be stored in a ```config.yaml``` file that uses the following format (with the exception of logLevel).  Note: this is not the same config file as your pmm config (it is speicifc to this application only).  Note: if you are using docker this file needs to be in the root of path that is mapped to "/config"

config.yaml:

```yaml
plex:
  serverUrl: <plex server url>
  token: <plex token>
  libraries:
    # List of your your plex libraries that you want to process and generate pmm configuration files.
    # - name: <<Name of your library>>
    #   path: <<relative path to store output>>
    #   pmm_path: <<optional path to your pmm config files for this library>>
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
* If you set the "pmm_path" in the libraries it will allow you to run a "delta" and only generate missing config files

Example:

```yaml
plex:
    serverUrl: ${PLEX_SERVER:-https://plex:32400}
    token: ${PLEX_TOKEN}
```
