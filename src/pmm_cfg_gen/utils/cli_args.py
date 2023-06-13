#!/usr/bin/env python3
###################################################################################################

import argparse
import logging

###################################################################################################

globalArgParser = argparse.ArgumentParser()

globalArgParser.add_argument(
    "--plex.serverUrl", 
    help="Plex Server fully qualifed URL"
)
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
    "--output.overwrite",
    default=False,
    help="Overwrite existing files (default: %(default)s)",
)

globalArgParser.add_argument(
    "--theMovieDatabase.apiKey",
    help="The Movie Database API Key"
)
globalArgParser.add_argument(
    "--thePosterDatabase.enablePro",
    action="store_true",
    default=None,
    help="Enable Pro features for The Poster Database (requires you to be able to login to the site)"
)

globalArgParser.add_argument(
    "--pmm.deltaOnly",
    action="store_true",
    default=None,
    help="Only generate files for items that do not already exist"
)

# Advanced Arguments
globalArgParser.add_argument(
    "--generate.types",
    nargs="*",
    choices=["library.any", "collection.any", "collection.movie", "collection.show", "collection.music", "collection.report", "metadata.any", "metadata.movie", "metadata.show", "metadata.music", "metadata.report", "report.any", "overlay.any", "overlay.movie", "overlay.show", "overlay.music", "overlay.report"],
    #default=["collection.any", "metadata.any", "report.any", "overlay.any"],
    default=None,
    #help="Comma delimited list of item types to generate (default: %(default)s)",
    help=argparse.SUPPRESS
)
globalArgParser.add_argument(
    "--generate.formats",
    nargs="*",
    choices=["json", "yaml", "html"],
    #default=["json", "yaml", "html"],
    default=None,
    #help="Comma delimited list of formats to generate (default: %(default)s)",
    help=argparse.SUPPRESS
)

globalArgParser.add_argument(
    "--logLevel",
    choices=["INFO", "WARN", "DEBUG", "CRITICAL"],
    default="INFO",
    help="Logging Level (default: %(default)s)",
)

###################################################################################################

globalArgs = globalArgParser.parse_args()
