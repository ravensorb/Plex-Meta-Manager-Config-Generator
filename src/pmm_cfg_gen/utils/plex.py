#!/usr/bin/env python3
###################################################################################################

import json
import logging
import os
from pathlib import Path

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
    __session: requests.Session

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
        # self.plexLibraryName = libraryName

    def process(self):
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
        self._logger.debug("Saving ThePosterDb Search Sumamry: {}".format(fileName))

        try:
            for key in self.thePostDbSearchCache:
                sorted(self.thePostDbSearchCache[key], key=lambda x: x["title"])
        except:
            self._logger.exception("Failed sorting the posterdatabase cache")

        writeFile(fileName, json.dumps(self.thePostDbSearchCache, indent=4))

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

        self.thePostDbSearchCache = dict()

        self._loadLibrary(libraryName)

        self._logger.info("Processing Library Collections")
        collections = self.plexLibrary.collections()

        for collection in collections:
            if not isPMMItem(collection) and collection.childCount > 0:
                try:
                    self._processCollection(collection.title, collection)
                except:
                    self._logger.exception(
                        "Error Processing Collection: {}".format(collection.title)
                    )
            else:
                self._logger.info("Skipping Collecton: {}".format(collection.title))

        self._logger.info("Processing Library Items")
        items = self.plexLibrary.all()

        for item in items:
            if not isPMMItem(item) and len(item.collections) == 0:
                try:
                    self._processMetadata(item.title, [item])
                except:
                    self._logger.exception(
                        "Error Processing Item: {}".format(item.title)
                    )
            else:
                self._logger.info(
                    "Skipping Metdata for: {} ({})".format(item.title, item.year)
                )

        self._saveThePosterDbSeachCache(
            Path(self.pathLibrary, "theposterdbsearch.json").resolve()
        )

        self._logger.info("Completed processing Library: '{}'".format(libraryName))

    def _processCollection(self, itemTitle, item):
        title = _cleanTitle(itemTitle)

        fileName = Path(self.pathLibrary, "collections", "{}.yml".format(title))
        fileNameJson = Path(
            self.pathLibrary, "collections/json", "{}.json".format(title)
        )

        self._logger.info("Generating Files for Collection: {}".format(itemTitle))

        tplFiles = globalSettingsMgr.settings.templates.collections.getByItemType(
            self.plexLibrary.type
        )
        self._logger.debug("tplFiles: {}".format(tplFiles))

        self._logger.debug("tplFileNamePMM: {}".format(tplFiles.pmmFileName))
        if not os.path.exists(fileName) and tplFiles.pmmFileName is not None:
            self.templateManager.renderAndSave(
                tplFiles.pmmFileName, fileName, tplArgs={"item": item}
            )
            # elif os.path.exists(fileName):
            # Do we want to try to merge here?
            # pmmCfgMgr = PlexMetaManager(self.pathLibrary)

            # pmmCfgMgr.mergeCollection(itemTitle, item)
            pass
        else:
            self._logger.warn("  Collection File Exists: {}".format(title))

        if (
            tplFiles.jsonFileName is not None
            and globalSettingsMgr.settings.generate.enableJson
        ):
            self.templateManager.renderAndSave(
                tplFiles.jsonFileName, fileNameJson, tplArgs={"item": item}
            )

        childItems = item.items()
        if len(childItems) > 0:
            self._processMetadata(title, childItems)

    def _processMetadata(self, itemTitle, items):
        title = _cleanTitle(itemTitle)

        itemsWithExtras = []
        for item in items:
            self._logger.info("{}: {} ({})".format(item.type, item.title, item.year))
            self._addItemToThePosterDbSearchCache(item)

            seasons = []
            if "childCount" in item.__dict__:
                self._logger.info("  Loading Seasons...")
                seasons = item.seasons()

            itemsWithExtras.append({"metadata": item, "seasons": seasons})

        fileName = Path(self.pathLibrary, "metadata", "{}.yml".format(title))
        fileNameJson = Path(self.pathLibrary, "metadata/json", "{}.json".format(title))

        tplFiles = globalSettingsMgr.settings.templates.metadata.getByItemType(
            self.plexLibrary.type
        )

        if not os.path.exists(fileName) and tplFiles.pmmFileName is not None:
            self.templateManager.renderAndSave(
                tplFiles.pmmFileName, fileName, tplArgs={"items": itemsWithExtras}
            )
        # elif os.path.exists(fileName):
        #     # Do we want to try to merge here?
        #     pass
        else:
            self._logger.warn("Metadata File Exists: {}".format(title))

        if (
            tplFiles.jsonFileName is not None
            and globalSettingsMgr.settings.generate.enableJson
        ):
            self.templateManager.renderAndSave(
                tplFiles.jsonFileName, fileNameJson, tplArgs={"items": itemsWithExtras}
            )
