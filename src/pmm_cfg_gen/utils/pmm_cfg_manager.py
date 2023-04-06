#!/usr/bin/env python3
###################################################################################################

import logging
import os
from pathlib import Path

import ruamel.yaml

from pmm_cfg_gen.utils.fileutils import formatLibraryItemPath, writeFile
from pmm_cfg_gen.utils.plex_utils import _cleanTitle, isPMMItem
from pmm_cfg_gen.utils.settings_yml import globalSettingsMgr
from pmm_cfg_gen.utils.template_manager import TemplateManager, generateTpDbUrl


###################################################################################################
class PlexMetaManager:
    _logger: logging.Logger

    pathLibrary: Path

    def __init__(self, pathLibrary: Path) -> None:
        self._logger = logging.getLogger("pmm_cfg_gen")

        self.pathLibrary = pathLibrary

        pass

    def mergeCollection(self, itemTitle: str, item):
        self._logger.info(
            "Merging Updates into Collection Item: '{}'".format(itemTitle)
        )

        title = _cleanTitle(itemTitle)

        fileName = Path(self.pathLibrary, "collections", "{}.yml".format(title))

        if os.path.exists(fileName):
            with open(fileName, "r") as fp:
                data = ruamel.yaml.load(
                    fp, ruamel.yaml.RoundTripLoader, preserve_quotes=True
                )

                if data is None:
                    return

                # self._logger.info("Data: {}".format(ruamel.yaml.dump(data)))

                for it in data[0]:
                    self._logger.info(ruamel.yaml.dump(it))
                    data["collections"][it].yaml_set_comment_before_after_key(
                        "template", after=format(generateTpDbUrl(item)), after_indent=2
                    )

            with open(fileName, "w") as fp:
                ruamel.yaml.dump(data, fp, Dumper=ruamel.yaml.RoundTripDumper)
        pass

    def mergeItem(self, itemTitle: str, item):
        title = _cleanTitle(itemTitle)

        fileName = Path(self.pathLibrary, "metadata", "{}.yml".format(title))

        if os.path.exists(fileName):
            with open(fileName, "r") as fp:
                data = ruamel.yaml.round_trip_load(fp)

                for it in data["metadata"]:
                    data["metadata"][it].yaml_set_comment_before_after_key(
                        "url_poster",
                        after=format(generateTpDbUrl(item)),
                        after_indent=2,
                    )
                    data["metadata"][it].yaml_set_comment_before_after_key(
                        "url_poster", after="IDs: ", after_indent=2
                    )

            with open(fileName, "w") as fp:
                ruamel.yaml.safe_dump(data, fp)

        pass
