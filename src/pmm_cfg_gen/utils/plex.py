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
from plexapi.collection import Collection
from plexapi.video import Video
from plexapi.server import PlexServer

from pmm_cfg_gen.utils.settings_utils_v2 import globalSettingsMgr, SettingsTemplateLibraryTypeEnum, SettingsTemplateFileFormatEnum
from pmm_cfg_gen.utils.file_utils import formatLibraryItemPath
from pmm_cfg_gen.utils.plex_stats import PlexStats
from pmm_cfg_gen.utils.plex_utils import PlexItemHelper, PlexVideoHelper, PlexCollectionHelper
from pmm_cfg_gen.utils.template_manager import TemplateManager
from pmm_cfg_gen.utils.template_filters import generateTpDbSearchUrl
from pmm_cfg_gen.utils.pmm_utils import PlexMetaManagerCache

###################################################################################################

# the following two lines disable InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


###################################################################################################
class PlexLibraryProcessor:
    _logger: logging.Logger

    __collectionProcessedCache: dict[str, list]
    __itemProcessedCache: dict[str, list]

    __plexMetaManagerCache: dict[str, PlexMetaManagerCache]

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

        self.__collectionProcessedCache = dict()
        self.__itemProcessedCache = dict()
        self.__plexMetaManagerCache = dict()

        self.templateManager = TemplateManager(
            globalSettingsMgr.settings.templates.getTemplateRootPath()
        )

    ###############################################################################################

    def process(self):
        self.__stats.timerProgram.start()

        self._connectToServer()

        if globalSettingsMgr.settings.plex.libraries is None:
            self._logger.debug("Loading Library list from plex.")
            globalSettingsMgr.settings.plex.libraries = sorted(
                [
                    str(x.title)
                    for x in self.plexServer.library.sections()
                    if x.type == "movie" or x.type == "show"
                ]
            )

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
            globalSettingsMgr.settings.output, library=self.plexLibrary
        )
        self.pathLibrary.mkdir(parents=True, exist_ok=True)

        self._logger.debug("Library Path: '{}'".format(self.pathLibrary))

        tplFiles = globalSettingsMgr.settings.templates.getTemplateByGroupAndLibraryType("library", self.plexLibrary.type)

        self._logger.debug(
            "Template Files for Library Type '{}': {}".format(self.plexLibrary.type, jsonpickle.dumps(tplFiles, unpicklable=False))
        )

        if tplFiles is not None:
            for tplFile in tplFiles:
                if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format):
                    fileName = Path(self.pathLibrary, "{}.{}".format(self.plexLibraryName, tplFile.fileExtension))

                    self.templateManager.renderAndSave(
                        tplFile.fileName, fileName, {"library": self.plexLibrary}
                    )

        if globalSettingsMgr.settings.plexMetaManager.cacheExistingFiles:
            self._logger.debug("Checking for Plex Meta Manager Cache enablement for this library")
            pmm = globalSettingsMgr.settings.plexMetaManager.getFolderByLibraryName(self.plexLibraryName)
            if pmm is not None:
                self._logger.info("Loading Plex Meta Manager File Cache")
                self._logger.debug("Plex Meta Manager Path: {}".format(pmm.path))
                self.__plexMetaManagerCache[libraryName].processFolder(pmm.path) 

        return self.plexLibrary

    def _processLibrary(self, libraryName: str):
        self._logger.info("-" * 50)
        self._logger.info("Started Processing Library: '{}'".format(libraryName))

        self.__stats.initLibrary(libraryName)
        self.__collectionProcessedCache.update({libraryName: list()})
        self.__itemProcessedCache.update({libraryName: list()})
        self.__plexMetaManagerCache.update({libraryName: PlexMetaManagerCache() })

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
                self._processMetadata(None, [item])
            except:
                self._logger.exception("Error Processing Item: {}".format(item.title))

        self.__stats.timerLibraries[libraryName].stop()

        self.__stats.countsLibraries[libraryName].calcTotals()
        self._saveCollectionReport()
        self._saveItemReport()

    def _processCollection(self, itemTitle: str, item):
        self.__stats.countsLibraries[self.plexLibraryName].collections.processed += 1

        if PlexItemHelper.isPMMItem(item) or item.childCount == 0:
            self._logger.info(
                "[{}/{}] Skipping Dynamic/Empty Collecton: {}".format(
                    self.__stats.countsLibraries[
                        self.plexLibraryName
                    ].collections.processed,
                    self.__stats.countsLibraries[
                        self.plexLibraryName
                    ].collections.total,
                    item.title,
                )
            )
            return

        self._logger.info(
            "[{}/{}] Processing Collection: {}".format(
                self.__stats.countsLibraries[
                    self.plexLibraryName
                ].collections.processed,
                self.__stats.countsLibraries[self.plexLibraryName].collections.total,
                itemTitle,
            )
        )

        pmmItem = self.__plexMetaManagerCache[self.plexLibraryName].collectionItem_to_dict(item.title)
        
        self._addCollectionToProcessedCache(item, pmmItem)

        tplFiles = globalSettingsMgr.settings.templates.getTemplateByGroupAndLibraryType("collection", self.plexLibrary.type)
        if tplFiles is None:
            self._logger.warn("No Collection Templates for type '{}' specifed".format(self.plexLibrary.type))

            return

        self._logger.debug(
            "Template Files for Collection Type '{}': {}".format(self.plexLibrary.type, jsonpickle.dumps(tplFiles, unpicklable=False))
        )

        fileNameBase = PlexItemHelper.formatString(globalSettingsMgr.settings.output.fileNameFormat.collections, library=self.plexLibrary, collection=item, item=None)

        for tplFile in tplFiles:
            try:
                if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format) and globalSettingsMgr.settings.generate.isTypeEnabled(tplFile.type):

                    if tplFile.subFolder is not None:
                        fileName = Path(self.pathLibrary, "collections", tplFile.subFolder, "{}.{}".format(fileNameBase, tplFile.fileExtension))
                    else: 
                        fileName = Path(self.pathLibrary, "collections", "{}.{}".format(fileNameBase, tplFile.fileExtension))

                    if not os.path.exists(fileName):
                        self.templateManager.renderAndSave(
                            tplFile.fileName, fileName, tplArgs={"item": item, "pmm": self.__plexMetaManagerCache[self.plexLibraryName].collectionItem_to_dict(item.title) } 
                        )
                    else:
                        self._logger.warn("  Collection File Name '{}' Exists. Skipping...".format(fileNameBase))
                else:
                    self._logger.debug("  Generating format '{}' for Collections is not enabled. Skipping...".format(tplFile.format))
            except:
                self._logger.exception("Error Processing Collection Template: {}".format(tplFile.fileName))

        childItems = item.items()
        if len(childItems) > 0:
            self.__stats.countsLibraries[self.plexLibraryName].items.total = len(
                childItems
            )
            self.__stats.countsLibraries[self.plexLibraryName].items.processed = 0

            self._processMetadata(collection=item, items=childItems)

    def _processMetadata(self, collection : Collection | None, items : list[Video]):

        tplFiles = globalSettingsMgr.settings.templates.getTemplateByGroupAndLibraryType("metadata", self.plexLibrary.type)
        if tplFiles is None:
            self._logger.warn("No Metadata Templates for type '{}' specifed".format(self.plexLibrary.type))

            return

        self._logger.debug(
            "Template Files for Metadata Type '{}': {}".format(self.plexLibrary.type, jsonpickle.dumps(tplFiles, unpicklable=False))
        )

        if collection is not None:
            fileNameBase = PlexItemHelper.formatString(globalSettingsMgr.settings.output.fileNameFormat.collections, library=self.plexLibrary, collection=collection, item=None)
        elif len(items) == 1 and isinstance(items[0], Video):
            fileNameBase = PlexItemHelper.formatString(globalSettingsMgr.settings.output.fileNameFormat.metadata, library=self.plexLibrary, collection=collection, item=items[0])
        else:
            self._logger.error("Invalid item attempted to be processed: {}".format(items))

            return

        self._logger.debug("Base FileName: {}".format(fileNameBase))

        itemsWithExtras: list[dict] = []
        
        for item in items:
            self.__stats.countsLibraries[self.plexLibraryName].items.processed += 1

            if PlexItemHelper.isPMMItem(item):
                self._logger.info(
                    "[{}/{}] Skipping '{}': {}. Dynamic item".format(
                        self.__stats.countsLibraries[
                            self.plexLibraryName
                        ].items.processed,
                        self.__stats.countsLibraries[self.plexLibraryName].items.total,
                        item.type,
                        PlexItemHelper.formatItemTitle(item),
                    )
                )
            elif self._isItemProcessed(item):
                self._logger.info(
                    "[{}/{}] Skipping {}: {}. Already Processed".format(
                        self.__stats.countsLibraries[
                            self.plexLibraryName
                        ].items.processed,
                        self.__stats.countsLibraries[self.plexLibraryName].items.total,
                        item.type,
                        PlexItemHelper.formatItemTitle(item),
                    )
                )
            else:
                self._logger.info(
                    "[{}/{}] Processing {}: {}".format(
                        self.__stats.countsLibraries[
                            self.plexLibraryName
                        ].items.processed,
                        self.__stats.countsLibraries[self.plexLibraryName].items.total,
                        item.type,
                        PlexItemHelper.formatItemTitle(item),
                    )
                )

                pmmItem = self.__plexMetaManagerCache[self.plexLibraryName].metadataItem_to_dict(item.title, item.year)

                self._addItemToProcessedCache(collection, item, pmmItem)

                itemDict = { "metadata": item, "pmm": pmmItem }
                
                seasons = []
                if "childCount" in item.__dict__:
                    self._logger.debug("  Loading Seasons...")
                    seasons = item.seasons()

                    itemDict.update({"seasons": seasons})

                itemsWithExtras.append(itemDict)

        # Do we have anything we need to process
        if len(itemsWithExtras) > 0:
            sorted(itemsWithExtras, key=lambda x: x["metadata"].year)

            for tplFile in tplFiles:
                try:
                    if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format) and globalSettingsMgr.settings.generate.isTypeEnabled(tplFile.type):
                        
                        if tplFile.subFolder is not None:
                            fileName = Path(self.pathLibrary, "metadata", tplFile.subFolder, "{}.{}".format(fileNameBase, tplFile.fileExtension))
                        else: 
                            fileName = Path(self.pathLibrary, "metadata", "{}.{}".format(fileNameBase, tplFile.fileExtension))

                        if not os.path.exists(fileName):
                            self.templateManager.renderAndSave(
                                tplFile.fileName, fileName, tplArgs={"items": itemsWithExtras } 
                            )
                        else:
                            self._logger.warn("  Metadata File Name '{}' Exists. Skipping...".format(fileNameBase))
                    else:
                        self._logger.debug("  Generating format '{}' for Metadata is not enabled. Skipping...".format(tplFile.format))
                except:
                    self._logger.exception("Error Processing Metadata Template: {}".format(tplFile.fileName))
                    
    def _isCollectionProcessed(self, item) -> bool:
        it = next(
            (
                x
                for x in self.__collectionProcessedCache[self.plexLibraryName]
                if x["title"] == item.title
            ),
            None,
        )

        return it is not None

    def _addCollectionToProcessedCache(self, item, pmmItem):
        if self.plexLibraryName not in self.__collectionProcessedCache.keys():
            self.__collectionProcessedCache[self.plexLibraryName] = []

        if not self._isCollectionProcessed(item):
            tpdbEntry = {
                "title": item.title,
                "searchUrl": generateTpDbSearchUrl(item),
                "metadata": item,
                "pmm": pmmItem if pmmItem is not None else {},
            }

            self.__collectionProcessedCache[self.plexLibraryName].append(tpdbEntry)

    def _isItemProcessed(self, item) -> bool:
        it = next(
            (
                x
                for x in self.__itemProcessedCache[self.plexLibraryName]
                if x["title"] == PlexItemHelper.formatItemTitle(item)
            ),
            None,
        )

        return it is not None

    def _addItemToProcessedCache(self, collection, item, pmmItem):
        pi = PlexVideoHelper(item)

        if self.plexLibraryName not in self.__itemProcessedCache.keys():
            self.__itemProcessedCache[self.plexLibraryName] = []

        if not self._isItemProcessed(item):
            tpdbEntry = {
                "collection": collection.title if collection is not None else "",
                "title": PlexItemHelper.formatItemTitle(item),
                "searchUrl": generateTpDbSearchUrl(item),
                "ids": pi.guids,
                "metadata": item,
                "pmm": pmmItem if pmmItem is not None else {},
            }

            self.__itemProcessedCache[self.plexLibraryName].append(tpdbEntry)

    def _saveCollectionReport(self):
        if not globalSettingsMgr.settings.generate.isTypeEnabled("report.any"):
            self._logger.debug("Skipping Saving Collection Report...")
            return

        self._logger.info("Saving Collection Report...")

        tplFiles = globalSettingsMgr.settings.templates.getTemplateByGroupAndLibraryType("collection", SettingsTemplateLibraryTypeEnum.REPORT)
        if tplFiles is None:
            self._logger.warn("No Collection Report Templates for type '{}' specifed".format(self.plexLibrary.type))

            return
                    
        self._logger.debug(
            "Template Files for Report Type '{}': {}".format(self.plexLibrary.type, jsonpickle.dumps(tplFiles, unpicklable=False))
        )

        self.__collectionProcessedCache[self.plexLibraryName] = sorted(
            self.__collectionProcessedCache[self.plexLibraryName],
            key=lambda x: x["title"],
        )

        fileNameBase = PlexItemHelper.formatString(globalSettingsMgr.settings.output.fileNameFormat.collectionsReport, library=self.plexLibrary, collection=None, item=None)
        
        for tplFile in tplFiles:
            try:
                if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format) and globalSettingsMgr.settings.generate.isTypeEnabled(tplFile.type):
                    
                    if tplFile.subFolder is not None:
                        fileName = Path(self.pathLibrary, "reports", tplFile.subFolder, "{}.{}".format(fileNameBase, tplFile.fileExtension))
                    else: 
                        fileName = Path(self.pathLibrary, "reports", "{}.{}".format(fileNameBase, tplFile.fileExtension))

                    if not os.path.exists(fileName):
                        self.templateManager.renderAndSave(
                            tplFile.fileName, fileName, tplArgs={
                                                                "items": self.__collectionProcessedCache[self.plexLibraryName],
                                                                "stats": json.loads(
                                                                    str(
                                                                        jsonpickle.dumps(
                                                                            self.__stats.countsLibraries[self.plexLibraryName],
                                                                            unpicklable=False,
                                                                        )
                                                                    )
                                                                ),
                                                                "processingTime": self.__stats.timerLibraries[
                                                                    self.plexLibraryName
                                                                ].to_dict()
                                                            }
                        )
                    else:
                        self._logger.warn("  Report File Name '{}' Exists. Skipping...".format(fileNameBase))
                else:
                    self._logger.debug("  Generating format '{}' for Report is not enabled. Skipping...".format(tplFile.format))
            except:
                self._logger.exception("Failed generating collection report: '{}'".format(tplFile.fileName))

    def _saveItemReport(self):
        if not globalSettingsMgr.settings.generate.isTypeEnabled("report.any"):
            self._logger.debug("Skipping Saving Item Report...")
            return

        self._logger.info("Saving Item Report...")

        tplFiles = globalSettingsMgr.settings.templates.getTemplateByGroupAndLibraryType("metadata", SettingsTemplateLibraryTypeEnum.REPORT)
        if tplFiles is None:
            self._logger.warn("No Item Report Templates for type '{}' specifed".format(self.plexLibrary.type))

            return
                    
        self._logger.debug(
            "Template Files for Report Type '{}': {}".format(self.plexLibrary.type, jsonpickle.dumps(tplFiles, unpicklable=False))
        )


        self.__itemProcessedCache[self.plexLibraryName] = sorted(
            self.__itemProcessedCache[self.plexLibraryName], key=lambda x: "{}:{}".format(x["collection"], x["title"])
        )

        fileNameBase = PlexItemHelper.formatString(globalSettingsMgr.settings.output.fileNameFormat.metadataReport, library=self.plexLibrary, collection=None, item=None)

        for tplFile in tplFiles:
            try:
                if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format) and globalSettingsMgr.settings.generate.isTypeEnabled(tplFile.type):
                    
                    if tplFile.subFolder is not None:
                        fileName = Path(self.pathLibrary, "reports", tplFile.subFolder, "{}.{}".format(fileNameBase, tplFile.fileExtension))
                    else: 
                        fileName = Path(self.pathLibrary, "reports", "{}.{}".format(fileNameBase, tplFile.fileExtension))

                    if not os.path.exists(fileName):
                        self.templateManager.renderAndSave(
                            tplFile.fileName, fileName, tplArgs={
                                                                "items": self.__itemProcessedCache[self.plexLibraryName],
                                                                "stats": json.loads(
                                                                    str(
                                                                        jsonpickle.dumps(
                                                                            self.__stats.countsLibraries[self.plexLibraryName],
                                                                            unpicklable=False,
                                                                        )
                                                                    )
                                                                ),
                                                                "processingTime": self.__stats.timerLibraries[
                                                                    self.plexLibraryName
                                                                ].to_dict(),                        
                                                            }
                        )
                    else:
                        self._logger.warn("  Report File Name '{}' Exists. Skipping...".format(fileNameBase))
                else:
                    self._logger.debug("  Generating format '{}' for Report is not enabled. Skipping...".format(tplFile.format))
            except:
                self._logger.exception("Failed generating item report: '{}'".format(tplFile.fileName))

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
                    libraryName, libraryTimer.elapsed_time_ts.to_str()
                )
            )

            self._logger.info(
                "  Collections: {}".format(libaryCounts.collections.total)
            )

            self._logger.info("  Items: {}".format(libaryCounts.items.total))

        self._logger.info("-" * 50)
