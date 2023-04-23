#!/usr/bin/env python3
###################################################################################################

import argparse
import logging

###################################################################################################

globalArgParser = argparse.ArgumentParser()

globalArgParser.add_argument(
    "--plex.serverUrl", 
    help="Plex Server fully qualifed URL")
globalArgParser.add_argument(
    "--plex.token", 
    help="Authentication Token (not claim token) for the plex server"
)
globalArgParser.add_argument(
    "--plex.lbraries", 
    nargs="*", 
    help="Comma delimited list of libraries to process"
)
globalArgParser.add_argument(
    "--output.path", 
    help="Root path to store generated files (default: ./data)"
)
globalArgParser.add_argument(
    "--generate.enableJson",
    action="store_true",
    default=False,
    help="Enabled generating json files for each item processed (default: %(default)s)",
)
globalArgParser.add_argument(
    "--generate.types",
    nargs="*",
    #default=["collection.any", "metadata.any", "report.any", "overlay.any"],
    help="Comma delimited list of item types to generate (default: %(default)s)",
)
globalArgParser.add_argument(
    "--generate.formats",
    nargs="*",
    #default=["json", "yaml", "html"],
    help="Comma delimited list of formats to generate (default: %(default)s)",
)

globalArgParser.add_argument(
    "--logLevel",
    choices=["INFO", "WARN", "DEBUG", "CRITICAL"],
    default="INFO",
    help="Logging Level (default: %(default)s)",
)

###################################################################################################

globalArgs = globalArgParser.parse_args()
