#!/usr/bin/env python3
#######################################################################

import logging
from pathlib import Path

from pmm_cfg_gen.utils.settings_utils_v1 import SettingsOutput, globalSettingsMgr
from pmm_cfg_gen.utils.plex_utils import PlexItemHelper

#######################################################################


def writeFile(fileName: str | Path, data: str):
    """
     Write data to file. If file doesn't exist it will be created. This is to avoid problems with non - existant directories
     
     @param fileName - Name of file to write
     @param data - Data to write to file ( string or file
    """
    logging.getLogger("pmm_cfg_gen").debug("Writing File: {}".format(fileName))

    p = Path(str(fileName))

    # Create a path to the parent directory if it doesn t exist.
    if not p.resolve().parent.exists():
        logging.getLogger("pmm_cfg_gen").debug(
            "Creating path: {}".format(p.resolve().parent)
        )
        p.resolve().parent.mkdir(parents=True, exist_ok=True)

    with open(p, "w") as f:
        f.write(data)


def formatLibraryItemPath(output: SettingsOutput, library=None, collection=None, item=None, pmm=None, librarySettings=None) -> Path:
    """
     Formats path with library and item information. This is used to make sure paths are formatted correctly when saving a library or item
     
     @param output - SettingsOutput object that contains settings for the currently edited file
     @param library - Library object that is going to be saved as a title
     @param item - Item object that is going to be saved as a title
     
     @return Path object that is ready to be saved to a file or None if there is no path to the
    """
    strPath = PlexItemHelper.formatString(output.pathFormat, library=library, collection=collection, item=item, pmm=pmm, librarySettings=librarySettings, cleanTitleStrings=True)

    return Path(output.path, strPath).resolve()
