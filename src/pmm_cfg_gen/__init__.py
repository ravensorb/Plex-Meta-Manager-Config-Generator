#!/usr/bin/env python3

#######################################################################

import logging
import os

from pmm_cfg_gen.utils.cli_args import globalArgs
from pmm_cfg_gen.utils.logging import setup_logging
from pmm_cfg_gen.utils.plex import PlexLibraryProcessor
from pmm_cfg_gen.utils.settings_yml import globalSettingsMgr

globalSettingsMgr.loadFromFile("config.yaml", globalArgs)

setup_logging(
    str(globalSettingsMgr.modulePath.joinpath("logging.yaml")),
    default_level=getattr(logging, globalArgs.logLevel),
)

logger = logging.getLogger("pmm_cfg_gen")
logger.setLevel(getattr(logging, globalArgs.logLevel))


def cli():
    plexMoveLibraryProcessor = PlexLibraryProcessor()
    plexMoveLibraryProcessor.process()


if __name__ == "__main__":
    cli()
