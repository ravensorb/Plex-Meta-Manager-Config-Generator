#!/usr/bin/env python3
#######################################################################

import logging
from pathlib import Path

from pmm_cfg_gen.utils.settings_yml import SettingsOutput, globalSettingsMgr

#######################################################################


def writeFile(fileName: str | Path, data: str):
    logging.getLogger("pmm_cfg_gen").debug("Writing File: {}".format(fileName))

    p = Path(fileName)

    if not p.resolve().parent.exists():
        logging.getLogger("pmm_cfg_gen").debug(
            "Creating path: {}".format(p.resolve().parent)
        )
        p.resolve().parent.mkdir(parents=True, exist_ok=True)

    with open(p, "w") as f:
        f.write(data)


def formatLibraryItemPath(output: SettingsOutput, library=None, item=None) -> Path:
    strPath = output.pathFormat

    if library is not None:
        strPath = strPath.replace("{{libraryTitle}}", library.title)
        strPath = strPath.replace("{{libraryType}}", library.type)

    if item is not None:
        strPath = strPath.replace("{{itemTitle}}", item.title)
        strPath = strPath.replace("{{itemType}}", item.type)

    return Path(output.path, strPath).resolve()
