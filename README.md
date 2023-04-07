# Plex-Meta-Mnager-Config-Generator
A python script to automatically generate Plex Meta Manager configuration files based on your plex libraries.

Install:
```pip install pmm-cfg-gen```

**Running from command line**

Usage:
```
usage: pmm-cfg-gen [-h] 
                    [--plex.serverUrl PLEX.SERVERURL] 
                    [--plex.token PLEX.TOKEN] 
                    [--plex.lbraries [PLEX.LBRARIES ...]] 
                    [--output.path OUTPUT.PATH] 
                    [--generate.enableJson] 
                    [--generate.enableThePosterDb]
                    [--logLevel {INFO,WARN,DEBUG,CRITICAL}]

options:
  -h, --help            show this help message and exit
  --plex.serverUrl PLEX.SERVERURL
                        Plex Server fully qualifed URL (Ex: https://plex:32400)
  --plex.token PLEX.TOKEN
                        Authentication Token (not claim token) for the plex server
  --plex.lbraries [PLEX.LBRARIES ...]
                        Comma delimited list of libraries to process
  --output.path OUTPUT.PATH
                        Root path to store generated files
  --generate.enableJson
                        Enabled generating json files for each item processed (default: False)
  --generate.enableThePosterDb
                        Enabled generating thePosterDb report (default: False)
  --logLevel {INFO,WARN,DEBUG,CRITICAL}
                        Logging Level (default: INFO)
```

**Configuration File**

All of the configuration can be stored in a ```config.yaml``` file that uses the following format (with the exception of logLevel).

config.yaml:
```
plex:
    serverUrl: <plex server>
    token: <plex token>
    output:
        path: <path to store generated output>
    generate:
        enableJson: <True/False>
        enableThePosterDb: <True/False>
    libraries:
        - <library 1>
        - <library 2>

```

Note: It is possible to use ENV variables (standard bash syntax supported).

Example:
```
plex:
    serverUrl: ${PLEX_SERVER:-https://plex:32400}
    token: ${PLEX_TOKEN}
```