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
from plexapi.audio import Artist
from plexapi.server import PlexServer

from pmm_cfg_gen.utils.settings_utils_v1 import globalSettingsMgr, SettingsTemplateLibraryTypeEnum, SettingsTemplateFileFormatEnum, SettingsPlexLibrary
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
    plexLibrarySettings: SettingsPlexLibrary

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
                    SettingsPlexLibrary(x.title)
                    for x in self.plexServer.library.sections()
                    if x.type == "movie" or x.type == "show"
                ], 
                key = lambda x: x.name
            )

        self._logger.info(
            "Libraries to process: {}".format(
                ",".join([ x.name for x in globalSettingsMgr.settings.plex.libraries ])
            )
        )
        for library in globalSettingsMgr.settings.plex.libraries:
            self._processLibrary(library)

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

    def _loadLibrary(self, library: SettingsPlexLibrary) -> LibrarySection:
        self._logger.debug("Loading plex library: {}".format(library.name))

        self.plexLibrarySettings = library
        self.plexLibrary = self.plexServer.library.section(self.plexLibrarySettings.name)
        
        self.__stats.initLibrary(self.plexLibrarySettings.name)
        self.__collectionProcessedCache.update({self.plexLibrarySettings.name: list()})
        self.__itemProcessedCache.update({self.plexLibrarySettings.name: list()})
        self.__plexMetaManagerCache.update({self.plexLibrarySettings.name: PlexMetaManagerCache() })

        self.__stats.timerLibraries[self.plexLibrarySettings.name].start()

        self.pathLibrary = formatLibraryItemPath(
            globalSettingsMgr.settings.output, library=self.plexLibrary, librarySettings=self.plexLibrarySettings
        )

        self.pathLibrary.mkdir(parents=True, exist_ok=True)

        globalSettingsMgr.settings.runtime.currentWorkingPath = str(self.pathLibrary)
        globalSettingsMgr.settings.runtime.currentWorkingPathRelative = str(self.pathLibrary.relative_to(Path(globalSettingsMgr.settings.output.path).resolve()))

        self._logger.debug("Library Path: '{}'".format(self.pathLibrary))

        tplFiles = globalSettingsMgr.settings.templates.getTemplateByGroupAndLibraryType("library", self.plexLibrary.type)

        self._logger.debug(
            "Template Files for Library Type '{}': {}".format(self.plexLibrary.type, jsonpickle.dumps(tplFiles, unpicklable=False))
        )

        if tplFiles is not None:
            for tplFile in tplFiles:
                if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format):
                    fileName = Path(self.pathLibrary, "{}.{}".format(self.plexLibrarySettings.path, tplFile.fileExtension))

                    self.templateManager.renderAndSave(
                        tplFile.fileName, fileName, {"library": self.plexLibrary}
                    )

        if globalSettingsMgr.settings.plexMetaManager.cacheExistingFiles:
            self._logger.debug("Checking for Plex Meta Manager Cache enablement for this library")
            if self.plexLibrarySettings.pmm_path is not None:
                self._logger.info("-" * 50)
                self._logger.info("Loading Plex Meta Manager File Cache")
                self._logger.debug("Plex Meta Manager Path: {}".format(self.plexLibrarySettings.pmm_path))
                self.__plexMetaManagerCache[self.plexLibrarySettings.name].processFolder(self.plexLibrarySettings.pmm_path) 
                self._logger.info("-" * 50)
                
        return self.plexLibrary

    def _processLibrary(self, library: SettingsPlexLibrary):
        self._logger.info("-" * 50)
        self._logger.info("Started Processing Library: '{}'".format(library.name))

        self._loadLibrary(library)

        self._logger.info("Processing Library Collections")
        collections = self.plexLibrary.collections()

        self._logger.info(f"Collections - Tota: {len(collections)}")

        self.__stats.countsLibraries[self.plexLibrarySettings.name].collections.total = len(collections)
        self.__stats.countsLibraries[self.plexLibrarySettings.name].collections.processed = 0

        self._saveCollectionTemplates()

        for collection in collections:
            try:
                self._processCollection(collection.title, collection)
            except:
                self._logger.exception(
                    "Error Processing Collection: {}".format(collection.title)
                )

        self._logger.info("Processing Library Items")
        items = self.plexLibrary.all()

        self._logger.info(f"Items - Total: {len(items)}")

        self.__stats.countsLibraries[self.plexLibrarySettings.name].items.total = len(items)
        self.__stats.countsLibraries[self.plexLibrarySettings.name].items.processed = 0
        self.__stats.countsLibraries[self.plexLibrarySettings.name].calcTotals()

        for item in items:
            try:
                self._processMetadata(None, [item])
            except:
                self._logger.exception("Error Processing Item: {}".format(item.title))

        self.__stats.timerLibraries[self.plexLibrarySettings.name].stop()

        self.__stats.countsLibraries[self.plexLibrarySettings.name].calcTotals()
        self.__stats.calcTotals()

        self._logger.info("-" * 50)        
        self._sortCache()
        #self._saveCollectionReport()
        #self._saveItemReport()
        self._saveReport("library", globalSettingsMgr.settings.output.fileNameFormat.libraryReport)
        self._saveReport("collection", globalSettingsMgr.settings.output.fileNameFormat.collectionsReport)
        self._saveReport("metadata", globalSettingsMgr.settings.output.fileNameFormat.metadataReport)

    def _processCollection(self, itemTitle: str, item):
        self.__stats.countsLibraries[self.plexLibrarySettings.name].collections.processed += 1

        if PlexItemHelper.isPMMItem(item) or item.childCount == 0:
            self._logger.info(
                "[{}/{}] Skipping {}: '{}'. [Reason: Dynamic/Empty Collecton]".format(
                    self.__stats.countsLibraries[
                        self.plexLibrarySettings.name
                    ].collections.processed,
                    self.__stats.countsLibraries[
                        self.plexLibrarySettings.name
                    ].collections.total,
                    item.type,
                    item.title,
                )
            )
            return

        pmmItem = self.__plexMetaManagerCache[self.plexLibrarySettings.name].collectionItem_to_dict(item.title)

        if pmmItem is not None and self.plexLibrarySettings.pmm_delta is True:
            self.__stats.countsLibraries[self.plexLibrarySettings.name].collections.skipped += 1

            self._logger.info(
                "[{}/{}] Skipping {}: '{}'. [Reason: Plex Meta Manager Cache Hit. Delta only requested]".format(
                    self.__stats.countsLibraries[
                        self.plexLibrarySettings.name
                    ].collections.processed,
                    self.__stats.countsLibraries[
                        self.plexLibrarySettings.name
                    ].collections.total,
                    item.type,
                    item.title,
                )
            )
            
            return
        
        self._logger.info(
            "[{}/{}] Processing {}: '{}'".format(
                self.__stats.countsLibraries[
                    self.plexLibrarySettings.name
                ].collections.processed,
                self.__stats.countsLibraries[self.plexLibrarySettings.name].collections.total,
                item.type,
                itemTitle,
            )
        )

        self._addCollectionToProcessedCache(item, pmmItem)

        tplFiles = globalSettingsMgr.settings.templates.getTemplateByGroupAndLibraryType("collection", self.plexLibrary.type)
        if tplFiles is None:
            self._logger.warn("\tNo Collection Templates for type '{}' specifed".format(self.plexLibrary.type))

            return

        self._logger.debug(
            "\tTemplate Files for Collection Type '{}': {}".format(self.plexLibrary.type, jsonpickle.dumps(tplFiles, unpicklable=False))
        )

        fileNameBase = PlexItemHelper.formatString(globalSettingsMgr.settings.output.fileNameFormat.collections, library=self.plexLibrary, collection=item, item=None, pmm=pmmItem, cleanTitleStrings=True)

        self._logger.debug("\tBase FileName: {}".format(fileNameBase))

        for tplFile in tplFiles:
            try:
                if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format) and globalSettingsMgr.settings.generate.isTypeEnabled(tplFile.type):

                    if tplFile.subFolder is not None:
                        fileName = Path(self.pathLibrary, "collections", tplFile.subFolder, "{}.{}".format(fileNameBase, tplFile.fileExtension))
                    else: 
                        fileName = Path(self.pathLibrary, "collections", "{}.{}".format(fileNameBase, tplFile.fileExtension))

                    if not os.path.exists(fileName) or globalSettingsMgr.settings.output.overwrite:
                        self.templateManager.renderAndSave(
                            tplFile.fileName, fileName, tplArgs={
                                "library": jsonpickle.dumps(self.plexLibrary, unpicklable=False),
                                "item": { 
                                    "metadata": item, 
                                    "pmm": pmmItem
                                }
                            } 
                        )
                    else:
                        self._logger.warn("\tCollection File Name '{}' Exists. Skipping...".format(fileNameBase))
                else:
                    self._logger.debug("\tGenerating format '{}' for Collections is not enabled. Skipping...".format(tplFile.format))
            except:
                self._logger.exception("\tError Processing Collection Template: {}".format(tplFile.fileName))

        childItems = item.items()
        if len(childItems) > 0:
            self.__stats.countsLibraries[self.plexLibrarySettings.name].items.total = len(
                childItems
            )
            self.__stats.countsLibraries[self.plexLibrarySettings.name].items.processed = 0

            self._processMetadata(collection=item, items=childItems)

    def _processMetadata(self, collection : Collection | None, items : list[Video]):

        tplFiles = globalSettingsMgr.settings.templates.getTemplateByGroupAndLibraryType("metadata", self.plexLibrary.type)
        if tplFiles is None:
            self._logger.warn("No Metadata Templates for type '{}' specifed".format(self.plexLibrary.type))

            return

        self._logger.debug(
            "Template Files for Metadata Type '{}': {}".format(self.plexLibrary.type, jsonpickle.dumps(tplFiles, unpicklable=False))
        )

        itemName: str = ""
        if collection is not None:
            itemName=collection.title
            
            pmmItem = self.__plexMetaManagerCache[self.plexLibrarySettings.name].collectionItem_to_dict(collection.title)
            
            fileNameBase = PlexItemHelper.formatString(globalSettingsMgr.settings.output.fileNameFormat.collections, library=self.plexLibrary, collection=collection, item=None, pmm=pmmItem, cleanTitleStrings=True)
        elif len(items) == 1 and (isinstance(items[0], Video) or isinstance(items[0], Artist)):
            itemName=items[0].title
            
            pmmItem = self.__plexMetaManagerCache[self.plexLibrarySettings.name].metadataItem_to_dict(items[0].title)
            
            fileNameBase = PlexItemHelper.formatString(globalSettingsMgr.settings.output.fileNameFormat.metadata, library=self.plexLibrary, collection=collection, item=items[0], pmm=pmmItem, cleanTitleStrings=True)
        else:
            self._logger.error("Invalid item attempted to be processed: {}".format(items))

            return
      
        self._logger.debug("Base FileName: {}".format(fileNameBase))

        itemsWithExtras: list[dict] = []
        
        for item in items:
            self.__stats.countsLibraries[self.plexLibrarySettings.name].items.processed += 1

            if pmmItem is not None and self.plexLibrarySettings.pmm_delta is True:
                self._logger.info(
                    "[{}/{}] Skipping {}: '{}'. [Reason: Plex Meta Manager Cache Hit. Delta only requested]".format(
                        self.__stats.countsLibraries[
                            self.plexLibrarySettings.name
                        ].items.processed,
                        self.__stats.countsLibraries[self.plexLibrarySettings.name].items.total,
                        item.type,
                        PlexItemHelper.formatItemTitle(item),
                    )
                )

                self.__stats.countsLibraries[self.plexLibrarySettings.name].items.skipped += 1

            elif PlexItemHelper.isPMMItem(item):
                self._logger.info(
                    "[{}/{}] Skipping {}: '{}'. [Reason: Dynamic item]".format(
                        self.__stats.countsLibraries[
                            self.plexLibrarySettings.name
                        ].items.processed,
                        self.__stats.countsLibraries[self.plexLibrarySettings.name].items.total,
                        item.type,
                        PlexItemHelper.formatItemTitle(item),
                    )
                )
            elif self._isItemProcessed(item):
                self._logger.info(
                    "[{}/{}] Skipping {}: '{}'. [Reason: Already Processed]".format(
                        self.__stats.countsLibraries[
                            self.plexLibrarySettings.name
                        ].items.processed,
                        self.__stats.countsLibraries[self.plexLibrarySettings.name].items.total,
                        item.type,
                        PlexItemHelper.formatItemTitle(item),
                    )
                )
            else:
                self._logger.info(
                    "[{}/{}] Processing {}: '{}'".format(
                        self.__stats.countsLibraries[
                            self.plexLibrarySettings.name
                        ].items.processed,
                        self.__stats.countsLibraries[self.plexLibrarySettings.name].items.total,
                        item.type,
                        PlexItemHelper.formatItemTitle(item),
                    )
                )

                pmmItem = self.__plexMetaManagerCache[self.plexLibrarySettings.name].metadataItem_to_dict(item.title, item.year if isinstance(item, Video) else None)

                self._addItemToProcessedCache(collection, item, pmmItem)

                itemDict = { "metadata": item, "pmm": pmmItem }

                if isinstance(item, Video):
                    seasons = []
                    if "childCount" in item.__dict__:
                        self._logger.debug("  Loading Seasons...")
                        seasons = item.seasons()

                        itemDict.update({"seasons": seasons})
                elif isinstance(item, Artist):
                    albums = item.albums()
                    itemDict.update({"albums": albums})

                    tracks = item.tracks()
                    itemDict.update({"tracks": tracks})

                itemsWithExtras.append(itemDict)

        # Do we have anything we need to process
        if len(itemsWithExtras) > 0:
            sorted(itemsWithExtras, key=lambda x: x["metadata"].year if x and "year" in x["metadata"].__dict__ else 0)

            for tplFile in tplFiles:
                try:
                    if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format) and globalSettingsMgr.settings.generate.isTypeEnabled(tplFile.type):
                        
                        if tplFile.subFolder is not None:
                            fileName = Path(self.pathLibrary, "metadata", tplFile.subFolder, "{}.{}".format(fileNameBase, tplFile.fileExtension))
                        else: 
                            fileName = Path(self.pathLibrary, "metadata", "{}.{}".format(fileNameBase, tplFile.fileExtension))

                        if not os.path.exists(fileName) or globalSettingsMgr.settings.output.overwrite:
                            self.templateManager.renderAndSave(
                                tplFile.fileName, fileName, tplArgs={
                                    "library": jsonpickle.dumps(self.plexLibrary, unpicklable=False),
                                    "items": itemsWithExtras 
                                } 
                            )
                        else:
                            self._logger.warn("  Metadata File Name '{}.{}' Exists. Skipping...".format(fileNameBase, tplFile.fileExtension))
                    else:
                        self._logger.debug("  Generating format '{}' for Metadata is not enabled. Skipping...".format(tplFile.format))
                except:
                    self._logger.exception("Error Processing Metadata Template: {}".format(tplFile.fileName))
                    
    def _isCollectionProcessed(self, item) -> bool:
        it = next(
            (
                x
                for x in self.__collectionProcessedCache[self.plexLibrarySettings.name]
                if x["title"] == item.title
            ),
            None,
        )

        return it is not None

    def _addCollectionToProcessedCache(self, item, pmmItem):
        if self.plexLibrarySettings.name not in self.__collectionProcessedCache.keys():
            self.__collectionProcessedCache[self.plexLibrarySettings.name] = []

        if not self._isCollectionProcessed(item):
            tpdbEntry = {
                "title": item.title,
                "searchUrl": generateTpDbSearchUrl(item),
                "metadata": item,
                "pmm": pmmItem if pmmItem is not None else {},
            }

            self.__collectionProcessedCache[self.plexLibrarySettings.name].append(tpdbEntry)

    def _isItemProcessed(self, item) -> bool:
        it = next(
            (
                x
                for x in self.__itemProcessedCache[self.plexLibrarySettings.name]
                if x["title"] == PlexItemHelper.formatItemTitle(item)
            ),
            None,
        )

        return it is not None

    def _addItemToProcessedCache(self, collection, item, pmmItem):
        pi = PlexVideoHelper(item)

        if self.plexLibrarySettings.name not in self.__itemProcessedCache.keys():
            self.__itemProcessedCache[self.plexLibrarySettings.name] = []

        if not self._isItemProcessed(item):
            tpdbEntry = {
                "collection": collection.title if collection is not None else "",
                "title": PlexItemHelper.formatItemTitle(item),
                "searchUrl": generateTpDbSearchUrl(item),
                "ids": pi.guids,
                "metadata": item,
                "pmm": pmmItem if pmmItem is not None else {},
            }

            self.__itemProcessedCache[self.plexLibrarySettings.name].append(tpdbEntry)

    def _sortCache(self):
        self.__collectionProcessedCache[self.plexLibrarySettings.name] = sorted(
            self.__collectionProcessedCache[self.plexLibrarySettings.name],
            key=lambda x: x["title"],
        )
        
        self.__itemProcessedCache[self.plexLibrarySettings.name] = sorted(
            self.__itemProcessedCache[self.plexLibrarySettings.name], key=lambda x: "{}:{}".format(x["collection"], x["title"])
        )

    def _saveCollectionTemplates(self):
        if not globalSettingsMgr.settings.generate.isTypeEnabled("collection.template"):
            self._logger.debug("Skipping Collection Templates...")
            return

        self._logger.info("Saving Collection Templates...")

        tplFiles = globalSettingsMgr.settings.templates.getTemplateByGroupAndLibraryType("collection", SettingsTemplateLibraryTypeEnum.TEMPLATE)
        if tplFiles is None:
            self._logger.warn("No Collection Templates for type '{}' specifed".format(self.plexLibrary.type))

            return
                    
        self._logger.debug(
            "Template Files for Template Type '{}': {}".format(self.plexLibrary.type, jsonpickle.dumps(tplFiles, unpicklable=False))
        )

        fileNameBase = PlexItemHelper.formatString(globalSettingsMgr.settings.output.fileNameFormat.template, library=self.plexLibrary, collection=None, item=None, cleanTitleStrings=True)
        
        for tplFile in tplFiles:
            try:
                if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format) and globalSettingsMgr.settings.generate.isTypeEnabled(tplFile.type):
                    
                    if tplFile.subFolder is not None:
                        fileName = Path(self.pathLibrary, "_templates", "{}.{}".format(fileNameBase, tplFile.fileExtension))
                    else: 
                        fileName = Path(self.pathLibrary, "_templates", "{}.{}".format(fileNameBase, tplFile.fileExtension))

                    if not os.path.exists(fileName) or globalSettingsMgr.settings.output.overwrite:
                        self.templateManager.renderAndSave(
                            tplFile.fileName, fileName, tplArgs={
                                                                "library": self.plexLibrary,
                                                                # "settings": globalSettingsMgr.settings
                                                            }
                        )
                    else:
                        self._logger.warn("  Template File Name '{}' Exists. Skipping...".format(fileNameBase))
                else:
                    self._logger.debug("  Generating format '{}' for Template is not enabled. Skipping...".format(tplFile.format))
            except:
                self._logger.exception("Failed generating collection template: '{}'".format(tplFile.fileName))

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

        fileNameBase = PlexItemHelper.formatString(globalSettingsMgr.settings.output.fileNameFormat.collectionsReport, library=self.plexLibrary, collection=None, item=None, cleanTitleStrings=True)
        
        for tplFile in tplFiles:
            try:
                if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format) and globalSettingsMgr.settings.generate.isTypeEnabled(tplFile.type):
                    
                    if tplFile.subFolder is not None:
                        fileName = Path(self.pathLibrary, "reports", tplFile.subFolder, "{}.{}".format(fileNameBase, tplFile.fileExtension))
                    else: 
                        fileName = Path(self.pathLibrary, "reports", "{}.{}".format(fileNameBase, tplFile.fileExtension))

                    if not os.path.exists(fileName) or globalSettingsMgr.settings.output.overwrite:
                        self.templateManager.renderAndSave(
                            tplFile.fileName, fileName, tplArgs=self._getTemplateArgs()
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

        fileNameBase = PlexItemHelper.formatString(globalSettingsMgr.settings.output.fileNameFormat.metadataReport, library=self.plexLibrary, collection=None, item=None, cleanTitleStrings=True)

        for tplFile in tplFiles:
            try:
                if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format) and globalSettingsMgr.settings.generate.isTypeEnabled(tplFile.type):
                    
                    if tplFile.subFolder is not None:
                        fileName = Path(self.pathLibrary, "reports", tplFile.subFolder, "{}.{}".format(fileNameBase, tplFile.fileExtension))
                    else: 
                        fileName = Path(self.pathLibrary, "reports", "{}.{}".format(fileNameBase, tplFile.fileExtension))

                    if not os.path.exists(fileName) or globalSettingsMgr.settings.output.overwrite:
                        self.templateManager.renderAndSave(
                            tplFile.fileName, fileName, tplArgs=self._getTemplateArgs()
                        )
                    else:
                        self._logger.warn("  Report File Name '{}' Exists. Skipping...".format(fileNameBase))
                else:
                    self._logger.debug("  Generating format '{}' for Report is not enabled. Skipping...".format(tplFile.format))
            except:
                self._logger.exception("Failed generating item report: '{}'".format(tplFile.fileName))

    def _saveReport(self, reportGroup : str, outputFormatString : str):
        if not globalSettingsMgr.settings.generate.isTypeEnabled("report.any") and not globalSettingsMgr.settings.generate.isTypeEnabled(f"{reportGroup}.report"):
            self._logger.info(f"Skipping Saving {reportGroup} Report...")
            return

        self._logger.info(f"Saving {reportGroup} Report...")

        tplFiles = globalSettingsMgr.settings.templates.getTemplateByGroupAndLibraryType(reportGroup, SettingsTemplateLibraryTypeEnum.REPORT)
        if tplFiles is None:
            self._logger.warn("No Item Report Templates for type '{}' specifed".format(self.plexLibrary.type))

            return
                    
        self._logger.debug(
            "Template Files for Report Type '{}': {}".format(self.plexLibrary.type, jsonpickle.dumps(tplFiles, unpicklable=False))
        )

        fileNameBase = PlexItemHelper.formatString(outputFormatString, library=self.plexLibrary, collection=None, item=None, cleanTitleStrings=True)

        for tplFile in tplFiles:
            try:
                self._logger.debug("Processing Report Template: '{}'".format(tplFile.fileName))
                
                if globalSettingsMgr.settings.generate.isFormatEnabled(tplFile.format) and globalSettingsMgr.settings.generate.isTypeEnabled(tplFile.type):
                    self._logger.info("  Generating format '{}' for Report".format(tplFile.format))
                    
                    if tplFile.subFolder is not None:
                        fileName = Path(self.pathLibrary, "reports", tplFile.subFolder, "{}.{}".format(fileNameBase, tplFile.fileExtension))
                    else: 
                        fileName = Path(self.pathLibrary, "reports", "{}.{}".format(fileNameBase, tplFile.fileExtension))

                    if not os.path.exists(fileName) or globalSettingsMgr.settings.output.overwrite:
                        self.templateManager.renderAndSave(
                            tplFile.fileName, fileName, tplArgs=self._getTemplateArgs()
                        )
                    else:
                        self._logger.warn("  Report File Name '{}' Exists. Skipping...".format(fileNameBase))
                else:
                    self._logger.info("  Generating format '{}' for Report is not enabled. Skipping...".format(tplFile.format))
            except:
                self._logger.exception("Failed generating report: '{}'".format(tplFile.fileName))

    def _displayHeader(self):
        self._logger.info("-" * 50)
        self._logger.info("Please Meta Manager Configuration File Generator")
        self._logger.info("-" * 50)

    def _displayStats(self):
        # self._logger.debug(json.dumps(self.__timers, indent=428, unpicklable=False))

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
            "  Items Processed: {}".format(self.__stats.countsProgram.items.total - self.__stats.countsProgram.items.skipped)
        )

        self._logger.info(
            "  Items Skipped: {}".format(self.__stats.countsProgram.items.skipped)
        )

        for libraryName in self.__stats.timerLibraries.keys():
            try:
                libraryTimer = self.__stats.timerLibraries[libraryName]
                libaryCounts = self.__stats.countsLibraries[libraryName]

                self._logger.info("Statistics for Library: '{}'".format(libraryName))

                self._logger.info(
                    "  Processing Time: '{}'. Total Time: {}".format(
                        libraryName, libraryTimer.elapsed_time_ts.to_str()
                    )
                )

                self._logger.info(
                    "  Collections Processed: {}".format(libaryCounts.collections.total)
                )

                self._logger.info(
                    "  Collections Skipped: {}".format(libaryCounts.collections.skipped)
                )

                self._logger.info("  Items Processed: {}".format(libaryCounts.items.total - libaryCounts.items.skipped))
                self._logger.info("  Items Skipped: {}".format(libaryCounts.items.skipped))
            except:
                self._logger.exception("Failed displaying stats for library: '{}'".format(libraryName))
                
        self._logger.info("-" * 50)

    def _getTemplateArgs(self):
        return {
            "library": self.plexLibrary,
            "collections": self.__collectionProcessedCache[self.plexLibrarySettings.name],
            "items": self.__itemProcessedCache[self.plexLibrarySettings.name],
            "stats": self.__stats.countsLibraries[self.plexLibrarySettings.name].toJson(),
            "processingTime": self.__stats.timerLibraries[self.plexLibrarySettings.name].to_dict()
        }
        
    # def _unlockAllLibraryFields(self):

    #     #self._logger.debug("Possible Fields: {}".format(self.plexLibrary.listFields(self.plexLibrary.type)))

    #     for field in self.plexLibrary.listFields(self.plexLibrary.type):
    #         self._logger.info("Unlocking Field: '{}'".format(field))
    #         try:
    #             self.plexLibrary.unlockAllField(field)
    #         except:
    #             self._logger.exception("Failed unlocking field: '{}'".format(field))
        