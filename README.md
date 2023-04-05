# Plex-Meta-Mnager-Config-Generator
A python script to automatically generate Plex Meta Manager configuration files based on your plex libraries.

Install:
```pip install pmm-cfg-gen```

**Running from command line**

Usage:
```
pmm-cfg-gen
pmm-cfg-gen -h | --help
pmm-cfg-gen --plex.serverUrl <plex server url> --plex.token <plex auth token> --plex.libraries <libray names> --output.path <path to store output> [--logLevel <log level>]
```

Options:
```
-h --help           Show this help
--plex.serverUrl    The Fully Qualified Name for your Plex Server (ex: https://plex:32400)
--plex.token        The Plex Auth token (not the claim token)
--plex.library      Comma delimited list of library names
--output.path       Set the output path (default: ./data)
--logLevel          Logging Level (INFO, WARN, DEBUG, CRITICAL)
```

**Configuration File**

All of the configuration can be stored in a ```config.yaml``` file that uses the following format.

config.yaml:
```
plex:
    serverUrl: <plex server>
    token: <plex token>
    libraries:
        - <library 1>
        - <library 2>
```
Note: It is possible to use ENV variables (standard bash syntax supported).
