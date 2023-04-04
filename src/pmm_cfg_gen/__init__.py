#!/usr/bin/env python3

#######################################################################

import logging 

import os
from pmm_cfg_gen.utils.cli_args import globalArgs
from pmm_cfg_gen.utils.plex import PlexLibraryProcessor
from pmm_cfg_gen.utils.settings_yml import globalSettingsMgr

logger = logging.getLogger("pmm_cfg_gen")
logger.setLevel(level=getattr(logging, globalArgs.logLevel))

ch=logging.StreamHandler()
ch.setLevel(level=getattr(logging, globalArgs.logLevel))
format = logging.Formatter('[%(asctime)s] (%(filename)25s:%(lineno)4s: %(funcName)30s) - %(levelname)8s - %(message)s')
ch.setFormatter(format)
logger.addHandler(ch)

def cli():
    globalSettingsMgr.loadFromFile("config.yaml", globalArgs)

    plexMoveLibraryProcessor = PlexLibraryProcessor()
    plexMoveLibraryProcessor.process()

if __name__ == "__main__":
    cli()