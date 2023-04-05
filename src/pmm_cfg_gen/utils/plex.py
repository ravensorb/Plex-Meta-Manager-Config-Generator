#!/usr/bin/env python3
###################################################################################################

import json
import logging
import os
import time
from pathlib import Path

import jsonpickle
import requests

# the following two lines disable InsecureRequestWarning
import urllib3
import urllib3.exceptions
from plexapi.library import LibrarySection
from plexapi.server import PlexServer

from pmm_cfg_gen.utils.fileutils import formatLibraryItemPath, writeFile
from pmm_cfg_gen.utils.plexutils import _cleanTitle, isPMMItem
from pmm_cfg_gen.utils.settings_yml import globalSettingsMgr
from pmm_cfg_gen.utils.template_manager import TemplateManager, generateTpDbUrl

###################################################################################################

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


###################################################################################################
class PlexLibraryProcessor:
    _logger: logging.Logger

    _libraryCounts = {}

    __session: requests.Session
    __timers: dict

    templateManager: TemplateManager

    plexServer: PlexServer
    plexLibrary: LibrarySection
    plexLibraryName: str

    pathLibrary: Path

    thePostDbSearchCache: dict

    ###############################################################################################
    def __init__(self) -> None:
        self._logger = logging.getLogger("pmm_cfg_gen")

        self.templateManager = TemplateManager(
            globalSettingsMgr.settings.templates.getTemplateRootPath()
        )

    def process(self):
        self.__timers = {}

        self.__timers.update({"program": {}, "library": {}})
        self.__timers["program"]["start"] = time.perf_counter()

        self.connectToServer()

        if globalSettingsMgr.settings.plex.libraries is None:
            self._logger.warn(
                "No plex libraries defined to process.  Please check your configuration"
            )
            return

        self._logger.debug(
            "Libraries to process: {}".format(
                ",".join(globalSettingsMgr.settings.plex.libraries)
            )
        )
        for libraryName in globalSettingsMgr.settings.plex.libraries:
            self._processLibrary(libraryName)

        self.__timers["program"]["end"] = time.perf_counter()

        self._dispalyTimings()

    def connectToServer(self):
        self._logger.info(
            "Connection to plex server: {}".format(
                globalSettingsMgr.settings.plex.serverUrl
            )
        )

        self.__session = requests.Session()
        self.__session.verify = False
        self.plexServer = PlexServer(
            globalSettingsMgr.settings.plex.serverUrl,
            globalSettingsMgr.settings.plex.token,
            session=self.__session,
        )

    ###############################################################################################
    def _loadLibrary(self, libraryName: str) -> LibrarySection:
        self._logger.debug("Loading plex library: {}".format(libraryName))

        self.plexLibrary = self.plexServer.library.section(libraryName)

        self.pathLibrary = formatLibraryItemPath(
            globalSettingsMgr.settings.output, self.plexLibrary
        )
        self.pathLibrary.mkdir(parents=True, exist_ok=True)

        self._logger.debug("Library Path: '{}'".format(self.pathLibrary))

        tplFiles = globalSettingsMgr.settings.templates.metadata.getByItemType(
            "library"
        )

        fileNameJson = Path(self.pathLibrary, "{}.json".format(libraryName))

        if (
            tplFiles.jsonFileName is not None
            and globalSettingsMgr.settings.generate.enableJson
        ):
            self.templateManager.renderAndSave(
                tplFiles.jsonFileName, fileNameJson, {"library": self.plexLibrary}
            )

        return self.plexLibrary

    def _saveThePosterDbSeachCache(self, fileName: str | Path):
        self._logger.info("Saving ThePosterDb Search Data: {}".format(fileName))

        tplFiles = globalSettingsMgr.settings.templates.thePosterDatabase
        if tplFiles is None:
            self._logger.warn("No PosterDatabase Templates specifed")
            return

        try:
            for key in self.thePostDbSearchCache:
                sorted(self.thePostDbSearchCache[key], key=lambda x: x["title"])

                fileNameHtml = Path(
                    self.pathLibrary,
                    "{}.{}.html".format("thePosterDatabaseSearch", key),
                )
                fileNameJson = Path(
                    self.pathLibrary,
                    "{}.{}.json".format("thePosterDatabaseSearch", key),
                )
                fileNameYaml = Path(
                    self.pathLibrary,
                    "{}.{}.yaml".format("thePosterDatabaseSearch", key),
                )

                if tplFiles.jsonFileName is not None and len(tplFiles.jsonFileName) > 0:
                    self.templateManager.renderAndSave(
                        tplFiles.jsonFileName,
                        fileNameJson,
                        tplArgs={"items": self.thePostDbSearchCache[key]},
                    )

                if tplFiles.htmlFileName is not None and len(tplFiles.htmlFileName) > 0:
                    self.templateManager.renderAndSave(
                        tplFiles.htmlFileName,
                        fileNameHtml,
                        tplArgs={"items": self.thePostDbSearchCache[key]},
                    )

                if tplFiles.yamlFileName is not None and len(tplFiles.yamlFileName) > 0:
                    self.templateManager.renderAndSave(
                        tplFiles.yamlFileName,
                        fileNameYaml,
                        tplArgs={"items": self.thePostDbSearchCache[key]},
                    )
        except:
            self._logger.exception("Failed storing the posterdatabase cache")

    def _addItemToThePosterDbSearchCache(self, item):
        ids = [o.id for o in item.guids]

        tpdbEntry = {
            "title": item.title,
            "searchUrl": generateTpDbUrl(item),
            "ids": ids,
        }

        if self.plexLibrary.type not in self.thePostDbSearchCache.keys():
            self.thePostDbSearchCache[self.plexLibrary.type] = []

        self.thePostDbSearchCache[self.plexLibrary.type].append(tpdbEntry)

    def _processLibrary(self, libraryName: str):
        self._logger.info("Started Processing Library: '{}'".format(libraryName))

        self.__timers["library"].update({libraryName: {}})
        self.__timers["library"][libraryName]["start"] = time.perf_counter()

        self.thePostDbSearchCache = dict()

        self._loadLibrary(libraryName)

        self._logger.info("Processing Library Collections")
        collections = self.plexLibrary.collections()

        self._libraryCounts.update(
            {
                "collections": {
                    "total": len(collections),
                    "processed": 0,
                    "items": {"total": 0, "processed": 0},
                }
            }
        )

        for collection in collections:
            self._libraryCounts["collections"]["processed"] += 1
            if not isPMMItem(collection) and collection.childCount > 0:
                try:
                    self._processCollection(collection.title, collection)
                except:
                    self._logger.exception(
                        "Error Processing Collection: {}".format(collection.title)
                    )
            else:
                self._logger.info(
                    "  Skipping Dynamic Collecton: {}".format(collection.title)
                )

        self._logger.info("Processing Library Items")
        items = self.plexLibrary.all()

        self._libraryCounts["collections"]["items"]["total"] = len(items)
        self._libraryCounts["collections"]["items"]["processed"] = 0

        for item in items:
            self._libraryCounts["collections"]["items"]["processed"] += 1

            if len(item.collections) == 0:
                self._logger.info(
                    "Skipping '{}' Metdata for {} ({}). Member of a collection".format(
                        item.type, item.title, item.year
                    )
                )
            elif isPMMItem(item):
                self._logger.info(
                    "Skipping '{}' Metdata for {} ({}). Dynamic item".format(
                        item.type, item.title, item.year
                    )
                )
            else:
                try:
                    self._processMetadata(item.title, [item])
                except:
                    self._logger.exception(
                        "Error Processing Item: {}".format(item.title)
                    )

        self._saveThePosterDbSeachCache(
            Path(
                self.pathLibrary, globalSettingsMgr.settings.thePosterDatabase.dataFile
            ).resolve()
        )

        self.__timers["library"][libraryName]["end"] = time.perf_counter()

    def _processCollection(self, itemTitle: str, item):
        title = _cleanTitle(itemTitle)

        fileName = Path(self.pathLibrary, "collections", "{}.yml".format(title))
        fileNameJson = Path(
            self.pathLibrary, "collections/json", "{}.json".format(title)
        )

        self._logger.info(
            "[{}/{}] Processing Collection: {}".format(
                self._libraryCounts["collections"]["processed"],
                self._libraryCounts["collections"]["total"],
                itemTitle,
            )
        )

        tplFiles = globalSettingsMgr.settings.templates.collections.getByItemType(
            self.plexLibrary.type
        )
        self._logger.debug(
            "tplFiles: {}".format(jsonpickle.dumps(tplFiles, unpicklable=False))
        )

        self._logger.debug("tplFileNameYaml: {}".format(tplFiles.yamlFileName))
        if (
            not os.path.exists(fileName)
            and tplFiles.yamlFileName is not None
            and globalSettingsMgr.settings.generate.enableYaml
        ):
            self._logger.info("  Generating Collection file")
            self.templateManager.renderAndSave(
                tplFiles.yamlFileName, fileName, tplArgs={"item": item}
            )
            # elif os.path.exists(fileName):
            # Do we want to try to merge here?
            # pmmCfgMgr = PlexMetaManager(self.pathLibrary)

            # pmmCfgMgr.mergeCollection(itemTitle, item)
            pass
        else:
            self._logger.warn("  Collection File Exists")

        self._logger.debug("tplFileNameJson: {}".format(tplFiles.jsonFileName))
        if (
            tplFiles.jsonFileName is not None
            and globalSettingsMgr.settings.generate.enableJson
        ):
            self._logger.info("  Generating json file")
            self.templateManager.renderAndSave(
                tplFiles.jsonFileName, fileNameJson, tplArgs={"item": item}
            )

        childItems = item.items()
        if len(childItems) > 0:
            self._libraryCounts["collections"]["items"]["total"] = len(childItems)
            self._libraryCounts["collections"]["items"]["processed"] = 0

            self._processMetadata(title, childItems)

    def _processMetadata(self, itemTitle: str, items):
        title = _cleanTitle(itemTitle)

        fileName = Path(self.pathLibrary, "metadata", "{}.yml".format(title))
        fileNameJson = Path(self.pathLibrary, "metadata/json", "{}.json".format(title))

        tplFiles = globalSettingsMgr.settings.templates.metadata.getByItemType(
            self.plexLibrary.type
        )

        itemsWithExtras = []
        for item in items:
            if len(items) > 1:
                self._libraryCounts["collections"]["items"]["processed"] += 1
            self._logger.info(
                "[{}/{}] Processing {}: {} ({})".format(
                    self._libraryCounts["collections"]["items"]["processed"],
                    self._libraryCounts["collections"]["items"]["total"],
                    item.type,
                    item.title,
                    item.year,
                )
            )

            self._addItemToThePosterDbSearchCache(item)

            seasons = []
            if "childCount" in item.__dict__:
                self._logger.info("  Loading Seasons...")
                seasons = item.seasons()

            itemsWithExtras.append({"metadata": item, "seasons": seasons})

        if (
            not os.path.exists(fileName)
            and tplFiles.yamlFileName is not None
            and globalSettingsMgr.settings.generate.enableYaml
        ):
            self._logger.info("  Generating Metdata file")
            self.templateManager.renderAndSave(
                tplFiles.yamlFileName, fileName, tplArgs={"items": itemsWithExtras}
            )
        # elif os.path.exists(fileName):
        #     # Do we want to try to merge here?
        #     pass
        else:
            self._logger.warn("  Metadata File Exists")

        if (
            tplFiles.jsonFileName is not None
            and globalSettingsMgr.settings.generate.enableJson
        ):
            self._logger.info("  Generating json file")
            self.templateManager.renderAndSave(
                tplFiles.jsonFileName, fileNameJson, tplArgs={"items": itemsWithExtras}
            )

    def _dispalyTimings(self):
        # self._logger.debug(json.dumps(self.__timers, indent=4, unpicklable=False))

        tdProgram = self.__timers["program"]["end"] - self.__timers["program"]["start"]
        self._logger.info("Total Processing Time: {:.2f} seconds".format(tdProgram))

        for libraryName in self.__timers["library"].keys():
            td = (
                self.__timers["library"][libraryName]["end"]
                - self.__timers["library"][libraryName]["start"]
            )
            self._logger.info(
                "  Processing Time for Library: '{}'. Total Time: {:.2f} seconds".format(
                    libraryName, td
                )
            )
