#!/usr/bin/env python3

#######################################################################

import logging
import os
import readchar
import signal

from pmm_cfg_gen.utils.cli_args import globalArgs
from pmm_cfg_gen.utils.logging import setup_logging
from pmm_cfg_gen.utils.plex import PlexLibraryProcessor
from pmm_cfg_gen.utils.settings_yml import globalSettingsMgr


def handler(signum, frame):
    msg = "Ctrl-c was pressed. Do you really want to exit? y/n "
    print(msg, end="", flush=True)
    res = readchar.readchar()
    if res == "y":
        print("")
        os._exit(1)
    else:
        print("", end="\r", flush=True)
        print(" " * len(msg), end="", flush=True)  # clear the printed line
        print("    ", end="\r", flush=True)


signal.signal(signal.SIGINT, handler)

setup_logging(
    str(globalSettingsMgr.modulePath.joinpath("logging.yaml")),
)

logger = logging.getLogger("pmm_cfg_gen")
logger.setLevel(getattr(logging, globalArgs.logLevel))

globalSettingsMgr.loadFromFile("config.yaml", globalArgs)


def cli():
    plexMoveLibraryProcessor = PlexLibraryProcessor()
    plexMoveLibraryProcessor.process()


if __name__ == "__main__":
    cli()
