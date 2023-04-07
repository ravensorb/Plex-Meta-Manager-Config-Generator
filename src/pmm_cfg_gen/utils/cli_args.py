#!/usr/bin/env python3
###################################################################################################

import argparse
import logging

###################################################################################################

globalArgParser = argparse.ArgumentParser()
globalArgParser.add_argument("--plex.serverUrl", help="Plex Server fully qualifed URL")
globalArgParser.add_argument(
    "--plex.token", help="Authentication Token (not claim token) for the plex server"
)
globalArgParser.add_argument(
    "--plex.lbraries", nargs="*", help="Commnd delimited list of libraries to process"
)
globalArgParser.add_argument("--output.path", help="Root path to store generated foles")
globalArgParser.add_argument(
    "--generate.enableJson",
    action="store_true",
    default=False,
    help="Enabled generating json files for each item processed (default: %(default)s)",
)
globalArgParser.add_argument(
    "--generate.enableThePosterDb",
    action="store_true",
    default=False,
    help="Enabled generating thePosterDb files (default: %(default)s)",
)

globalArgParser.add_argument(
    "--logLevel",
    choices=["INFO", "WARN", "DEBUG", "CRITICAL"],
    default="INFO",
    help="Logging Level (default: %(default)s)",
)

###################################################################################################

globalArgs = globalArgParser.parse_args()
