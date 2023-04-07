#!/usr/bin/env python3
###################################################################################################

import json
import logging
import os
from pathlib import Path

import jsonpickle
import requests

import urllib3
import urllib3.exceptions
from plexapi.library import LibrarySection
from plexapi.server import PlexServer

from pmm_cfg_gen.utils.fileutils import formatLibraryItemPath
from pmm_cfg_gen.utils.plex_stats import (
    PlexStats
)
from pmm_cfg_gen.utils.plex_utils import _cleanTitle, isPMMItem, _formatItemTitle
from pmm_cfg_gen.utils.settings_yml import globalSettingsMgr
from pmm_cfg_gen.utils.template_manager import TemplateManager, generateTpDbUrl

###################################################################################################

# the following two lines disable InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


###################################################################################################
class PlexLibraryProcessor:
    _logger: logging.Logger
    _itemProcessedCache: dict[str,list]

    __session: requests.Session

    __stats: PlexStats

    templateManager: TemplateManager

    plexServer: PlexServer
    plexLibrary: LibrarySection
    plexLibraryName: str

    pathLibrary: Path


    ###############################################################################################
    def __init__(self) -> None:
        self._logger = logging.getLogger("pmm_cfg_gen")
        self._displayHeader()

        self.__stats = PlexStats()

        self._itemProcessedCache = dict()

        self.templateManager = TemplateManager(
            globalSettingsMgr.settings.templates.getTemplateRootPath()
        )

    ###############################################################################################

    def process(self):
        self.__stats.timerProgram.start()

        self._connectToServer()

        
        if globalSettingsMgr.settings.plex.libraries is None:
            self._logger.debug(
                "Loading Library list from plex."
            )
            globalSettingsMgr.settings.plex.libraries = sorted([str(x.title) for x in self.plexServer.library.sections() if x.type == "movie" or x.type == "show"])

        self._logger.info(
            "Libraries to process: {}".format(
                ",".join(globalSettingsMgr.settings.plex.libraries)
            )
        )
        for libraryName in globalSettingsMgr.settings.plex.libraries:
            self._processLibrary(libraryName)

        self.__stats.timerProgram.stop()
        self.__stats.calcTotals()

        self._displayStats()

    ###############################################################################################
    def _connectToServer(self):
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

    def _loadLibrary(self, libraryName: str) -> LibrarySection:
        self._logger.debug("Loading plex library: {}".format(libraryName))

        self.plexLibrary = self.plexServer.library.section(libraryName)
        self.plexLibraryName = libraryName

        self.pathLibrary = formatLibraryItemPath(
            globalSettingsMgr.settings.output, self.plexLibrary
        )
        self.pathLibrary.mkdir(parents=True, exist_ok=True)

        self._logger.debug("Library Path: '{}'".format(self.pathLibrary))

        if globalSettingsMgr.settings.generate.enableJson:
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

    def _processLibrary(self, libraryName: str):
        self._logger.info("-" * 50)
        self._logger.info("Started Processing Library: '{}'".format(libraryName))

        self.__stats.initLibrary(libraryName)
        self._itemProcessedCache.update({ libraryName : list() })

        self.__stats.timerLibraries[libraryName].start()

        self._loadLibrary(libraryName)

        self._logger.info("Processing Library Collections")
        collections = self.plexLibrary.collections()

        self.__stats.countsLibraries[libraryName].collections.total = len(collections)
        self.__stats.countsLibraries[libraryName].collections.processed = 0

        for collection in collections:
            try:
                self._processCollection(collection.title, collection)
            except:
                self._logger.exception(
                    "Error Processing Collection: {}".format(collection.title)
                )

        self._logger.info("Processing Library Items")
        items = self.plexLibrary.all()

        self.__stats.countsLibraries[libraryName].items.total = len(items)
        self.__stats.countsLibraries[libraryName].items.processed = 0
        self.__stats.countsLibraries[libraryName].calcTotals()

        for item in items:
            try:
                self._processMetadata(item.title, [item])
            except:
                self._logger.exception(
                    "Error Processing Item: {}".format(item.title)
                )

        self.__stats.timerLibraries[libraryName].stop()

        self.__stats.countsLibraries[libraryName].calcTotals()
        self._saveThePosterDbSeachCache()

    def _processCollection(self, itemTitle: str, item):
        self.__stats.countsLibraries[self.plexLibraryName].collections.processed += 1

        title = _cleanTitle(itemTitle)

        if isPMMItem(item) or item.childCount == 0:
            self._logger.info(
                "[{}/{}] Skipping Dynamic/Empty Collecton: {}".format(
                    self.__stats.countsLibraries[self.plexLibraryName].collections.processed,
                    self.__stats.countsLibraries[self.plexLibraryName].collections.total,
                    item.title)
            )
            return 
        
        self._logger.info(
            "[{}/{}] Processing Collection: {}".format(
                self.__stats.countsLibraries[self.plexLibraryName].collections.processed,
                self.__stats.countsLibraries[self.plexLibraryName].collections.total,
                itemTitle,
            )
        )

        tplFiles = globalSettingsMgr.settings.templates.collections.getByItemType(
            self.plexLibrary.type
        )
        self._logger.debug(
            "tplFiles: {}".format(jsonpickle.dumps(tplFiles, unpicklable=False))
        )

        fileName = Path(self.pathLibrary, "collections", "{}.yml".format(title))
        if (
            not os.path.exists(fileName)
            and tplFiles.yamlFileName is not None
            and globalSettingsMgr.settings.generate.enableYaml
        ):
            self._logger.debug("  Generating Collection file")
            
            self.templateManager.renderAndSave(
                tplFiles.yamlFileName, fileName, tplArgs={"item": item}
            )
            # elif os.path.exists(fileName):
            # Do we want to try to merge here?
            # pmmCfgMgr = PlexMetaManager(self.pathLibrary)

            # pmmCfgMgr.mergeCollection(itemTitle, item)
            pass
        elif not globalSettingsMgr.settings.generate.enableYaml:
            self._logger.debug("  Skipping Generating Collection yaml file")
        else:
            self._logger.warn("  Collection File Exists")

        fileNameJson = Path(self.pathLibrary, "collections/json", "{}.json".format(title))
        if (
            tplFiles.jsonFileName is not None
            and globalSettingsMgr.settings.generate.enableJson
        ):
            self._logger.debug("  Generating json file")
            self.templateManager.renderAndSave(
                tplFiles.jsonFileName, fileNameJson, tplArgs={"item": item}
            )
        elif not globalSettingsMgr.settings.generate.enableJson:
            self._logger.debug("  Skipping Geerating json file")

        childItems = item.items()
        if len(childItems) > 0:
            self.__stats.countsLibraries[self.plexLibraryName].items.total = len(
                childItems
            )
            self.__stats.countsLibraries[self.plexLibraryName].items.processed = 0

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
            self.__stats.countsLibraries[self.plexLibraryName].items.processed += 1

            if isPMMItem(item):
                self._logger.info(
                    "[{}/{}] Skipping '{}': {}. Dynamic item".format(
                        self.__stats.countsLibraries[self.plexLibraryName].items.processed,
                        self.__stats.countsLibraries[self.plexLibraryName].items.total,
                        item.type, _formatItemTitle(item)
                    )
                )
            elif self._isItemProcessed(item):                                 
                self._logger.info(
                    "[{}/{}] Skipping {}: {}. Already Processed".format(
                        self.__stats.countsLibraries[self.plexLibraryName].items.processed,
                        self.__stats.countsLibraries[self.plexLibraryName].items.total,
                        item.type,
                        _formatItemTitle(item)
                    )
                )
            else:
                self._logger.info(
                    "[{}/{}] Processing {}: {}".format(
                        self.__stats.countsLibraries[self.plexLibraryName].items.processed,
                        self.__stats.countsLibraries[self.plexLibraryName].items.total,
                        item.type,
                        _formatItemTitle(item)
                    )
                )

                self._adItemToProcessedCache(item)

                seasons = []
                if "childCount" in item.__dict__:
                    self._logger.debug("  Loading Seasons...")
                    seasons = item.seasons()

                itemsWithExtras.append({"metadata": item, "seasons": seasons})

        if (
            not os.path.exists(fileName)
            and tplFiles.yamlFileName is not None
            and globalSettingsMgr.settings.generate.enableYaml
        ):
            self._logger.debug("  Generating Metdata file")
            self.templateManager.renderAndSave(
                tplFiles.yamlFileName, fileName, tplArgs={"items": itemsWithExtras}
            )
        # elif os.path.exists(fileName):
        #     # Do we want to try to merge here?
        #     pass
        else:
            self._logger.debug("  Metadata File Exists")

        if (
            tplFiles.jsonFileName is not None
            and globalSettingsMgr.settings.generate.enableJson
        ):
            self._logger.debug("  Generating json file")
            self.templateManager.renderAndSave(
                tplFiles.jsonFileName, fileNameJson, tplArgs={"items": itemsWithExtras}
            )

    def _isItemProcessed(self, item) -> bool:
        it = next(
            (
                x
                for x in self._itemProcessedCache[self.plexLibraryName]
                if x["title"] ==  _formatItemTitle(item)
            ),
            None,
        )

        return it is not None 
            
    def _adItemToProcessedCache(self, item):
        ids = [o.id for o in item.guids]

        if self.plexLibraryName not in self._itemProcessedCache.keys():
            self._itemProcessedCache[self.plexLibraryName] = []

        if not self._isItemProcessed(item):
            tpdbEntry = {
                "title":  _formatItemTitle(item),
                "searchUrl": generateTpDbUrl(item),
                "ids": ids,
            }

            self._itemProcessedCache[self.plexLibraryName].append(tpdbEntry)

    def _saveThePosterDbSeachCache(self):
        if not globalSettingsMgr.settings.generate.enaleThePosterDb:
            self._logger.debug("Skipping Saving ThPosterDb Search Data...")
            return

        self._logger.info("Saving ThePosterDb Search Data")

        tplFiles = globalSettingsMgr.settings.templates.thePosterDatabase
        if tplFiles is None:
            self._logger.warn("No PosterDatabase Templates specifed")
            return

        try:
            self._itemProcessedCache[self.plexLibraryName] = sorted(
                self._itemProcessedCache[self.plexLibraryName], key=lambda x: x["title"]
            )

            fileNameJson = Path(self.pathLibrary, "{}.json".format(globalSettingsMgr.settings.thePosterDatabase.baseFileName) )
            if tplFiles.jsonFileName is not None and len(tplFiles.jsonFileName) > 0:
                self.templateManager.renderAndSave(
                    tplFiles.jsonFileName,
                    fileNameJson,
                    tplArgs={
                        "items": self._itemProcessedCache[self.plexLibraryName],
                        "stats": json.loads(str(jsonpickle.dumps(self.__stats.countsLibraries[self.plexLibraryName], unpicklable=False))),
                        "processingTime": self.__stats.timerLibraries[self.plexLibraryName].to_dict()
                    }
                )

            fileNameHtml = Path(self.pathLibrary, "{}.html".format(globalSettingsMgr.settings.thePosterDatabase.baseFileName) )
            if tplFiles.htmlFileName is not None and len(tplFiles.htmlFileName) > 0:
                self.templateManager.renderAndSave(
                    tplFiles.htmlFileName,
                    fileNameHtml,
                    tplArgs={
                        "items": self._itemProcessedCache[self.plexLibraryName],
                        "stats": json.loads(str(jsonpickle.dumps(self.__stats.countsLibraries[self.plexLibraryName], unpicklable=False))),
                        "processingTime": self.__stats.timerLibraries[self.plexLibraryName].to_dict()
                    }
                )

            fileNameYaml = Path(self.pathLibrary, "{}.yaml".format(globalSettingsMgr.settings.thePosterDatabase.baseFileName) )
            if tplFiles.yamlFileName is not None and len(tplFiles.yamlFileName) > 0:
                self.templateManager.renderAndSave(
                    tplFiles.yamlFileName,
                    fileNameYaml,
                    tplArgs={
                        "items": self._itemProcessedCache[self.plexLibraryName],
                        "stats": json.loads(str(jsonpickle.dumps(self.__stats.countsLibraries[self.plexLibraryName], unpicklable=False))),
                        "processingTime": self.__stats.timerLibraries[self.plexLibraryName].to_dict()
                    }
                )
        except:
            self._logger.exception("Failed storing the posterdatabase cache")

    def _displayHeader(self):
        self._logger.info("-" * 50)
        self._logger.info("Please Meta Manager Configuration File Generator")
        self._logger.info("-" * 50)

    def _displayStats(self):
        # self._logger.debug(json.dumps(self.__timers, indent=4, unpicklable=False))

        self._logger.info("-" * 50)

        self._logger.info("Overall Statistics")

        self._logger.info(
            "  Total Processing Time: {}".format(
                    self.__stats.timerProgram.elapsed_time_ts.to_str() 
                )            
        )
        self._logger.info(
            "  Collections Processed: {}".format(
                self.__stats.countsProgram.collections.total
            )
        )
        self._logger.info(
            "  Items Processed: {}".format(self.__stats.countsProgram.items.total)
        )

        for libraryName in self.__stats.timerLibraries.keys():
            libraryTimer = self.__stats.timerLibraries[libraryName]
            libaryCounts = self.__stats.countsLibraries[libraryName]

            self._logger.info("Statistics for Library: '{}'".format(libraryName))

            self._logger.info(
                "  Processing Time: '{}'. Total Time: {}".format(
                    libraryName, 
                    libraryTimer.elapsed_time_ts.to_str()
                )
            )

            self._logger.info(
                "  Collections: {}".format(libaryCounts.collections.total)
            )

            self._logger.info("  Items: {}".format(libaryCounts.items.total))

        self._logger.info("-" * 50)
