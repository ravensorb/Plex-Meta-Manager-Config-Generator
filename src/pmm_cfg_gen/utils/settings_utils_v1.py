#!/usr/bin/env python3

#######################################################################

from typing import List
from enum import Enum

import logging
import os
from pathlib import Path

import confuse
import importlib_resources
import jsonpickle
from dotenv import load_dotenv
from expandvars import expandvars

#######################################################################

class SettingsTemplateFileFormatEnum(Enum):
    HTML = "html"
    JSON = "json"
    YAML = "yaml"


class SettingsTemplateLibraryTypeEnum(Enum):
    ANY = "any"
    LIBRARY = "library"
    MOVIE = "movie"
    MUSIC = "music"
    REPORT = "report"
    SHOW = "show"
    TEMPLATE = "template"


class SettingsGenerate:
    types: list[str]
    formats: list[str]

    def __init__(self, types: list[str], formats: list[str]) -> None:
        self.types = types
        self.formats = formats

    def isFormatEnabled(self, formatValue: SettingsTemplateFileFormatEnum | str) -> bool:
        if isinstance(formatValue, SettingsTemplateFileFormatEnum):
            formatValue = formatValue.value

        formatValue = str(formatValue).lower()

        logging.getLogger("pmm_cfg_gen").debug(f"Checking if format '{formatValue}' is enabled (formats: {self.formats})")

        return formatValue in self.formats
        
    def isTypeEnabled(self, typeValue: SettingsTemplateLibraryTypeEnum | str) -> bool:
        if isinstance(typeValue, SettingsTemplateLibraryTypeEnum):
            typeValue = typeValue.value

        typeValue = str(typeValue).lower()

        logging.getLogger("pmm_cfg_gen").debug(f"Checking if type '{typeValue}' is enabled (types: {self.types})")

        typeValueParts = typeValue.split(".")
        if len(typeValueParts) > 1:
            if f"{typeValueParts[0]}.any" in self.types:
                return True

        return typeValue in self.types


class SettingsOutputFileNames:
    library : str
    collections: str
    metadata: str
    libraryReport : str
    collectionsReport: str
    metadataReport: str
    report: str
    template: str

    def __init__(self, library: str, collections: str, metadata: str, libraryReport: str, collectionsReport: str, metadataReport: str, report: str, template: str) -> None:
        self.library = library
        self.collections = collections
        self.metadata = metadata

        self.libraryReport = libraryReport
        self.collectionsReport = collectionsReport
        self.metadataReport = metadataReport
        self.report = report
        
        self.template = template


class SettingsOutput:
    path: str
    pathFormat: str
    sharedTemplatePathFormat: str
    fileNameFormat: SettingsOutputFileNames
    overwrite: bool

    def __init__(self, path: str, pathFormat: str, sharedTemplatePathFormat: str, overwrite : bool, fileNameFormat: SettingsOutputFileNames) -> None:
        self.path = path
        self.pathFormat = pathFormat
        self.sharedTemplatePathFormat = sharedTemplatePathFormat
        self.fileNameFormat = fileNameFormat
        self.overwrite = overwrite


class SettingsPmmDefaults:
    deltaOnly: bool
    basePath: str | None

    def __init__(self, deltaOnly: bool = False, basePath: str | None = None) -> None:
        self.deltaOnly = deltaOnly
        self.basePath = expandvars(basePath.strip()) if basePath is not None else None        

class SettingsPlexLibrary:
    name: str
    path: str | None
    pmm_path: str | None
    pmm_delta: bool | None

    def __init__(self, name: str, path: str | None = None, pmm_path: str | None = None, pmm_delta: bool | None = None) -> None:
        self.name = name.strip()
        self.path = path.strip() if path is not None else name.strip()
        self.pmm_path = pmm_path.strip() if pmm_path is not None else None
        self.pmm_delta = pmm_delta 


class SettingsPlexServer:
    serverUrl: str
    token: str
    libraries: list[SettingsPlexLibrary]

    def __init__(self, serverUrl: str, token: str, libraries: List, pmmDefaults: SettingsPmmDefaults | None = None) -> None:
        self.serverUrl = serverUrl
        self.token = token

        if libraries is not None:
            self.libraries = []
            
            for library in libraries:
                if isinstance(library, dict):
                    self.libraries += [SettingsPlexLibrary(**library)]
                elif isinstance(library, str):
                    self.libraries += [SettingsPlexLibrary(name=library)]

        if pmmDefaults is not None:
            for library in self.libraries:
                
                if library.pmm_delta is None:
                    library.pmm_delta = pmmDefaults.deltaOnly
                    
                if library.path is None and pmmDefaults.basePath is not None:
                    library.path = os.path.join(pmmDefaults.basePath, library.name)
                        
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            data["serverUrl"],
            data["token"],
            data["libraries"]
        )
                    

class SettingsPlexMetaManager:
    cacheExistingFiles: bool

    def __init__(self, cacheExistingFiles: bool) -> None: 
        self.cacheExistingFiles = cacheExistingFiles

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            data["cacheExistingFiles"],
            # [SettingsPlexMetaManagerFolder.from_dict(x) for x in data["folders"]]
        )


class SettingsTemplateFile:
    type: str
    format: str
    fileName: str
    fileExtension: str
    subFolder: str | None

    def __init__(self, type: str, format: str, fileName: str, fileExtension : str | None, subFolder : str | None) -> None:
        self.type = type
        self.format = format
        self.fileName = fileName
        self.fileExtension = fileExtension if fileExtension is not None else str(format).lower()
        self.subFolder = subFolder

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            data["type"],
            data["format"],
            data["file"],
            data["fileExtension"] if "fileExtension" in data else None,
            data["subFolder"] if "subFolder" in data else None,
        )

    @classmethod
    def from_list_dict(cls, data: List[dict]):
        return [cls.from_dict(x) for x in data]


class SettingsTemplateGroups:
    templatePath : str | None
    library: List[SettingsTemplateFile]
    collection: List[SettingsTemplateFile]
    metadata: List[SettingsTemplateFile]
    overlay: List[SettingsTemplateFile]

    def __init__(self, library: List[SettingsTemplateFile], collection: List[SettingsTemplateFile], metadata: List[SettingsTemplateFile], overlay: List[SettingsTemplateFile], templatePath : str | None) -> None:
        self.library = library
        self.collection = collection
        self.metadata = metadata
        self.overlay = overlay
        self.templatePath = templatePath

    def getTemplateRootPath(self) -> Path:
        if self.templatePath is None or self.templatePath == "pmm_cfg_gen.tempaltes":
            self.templatePath = str(
                importlib_resources.files("pmm_cfg_gen").joinpath("templates")
            )

        return Path(self.templatePath).resolve()

    def getTemplateByGroupName(self, name: str) -> List[SettingsTemplateFile]:

        result: List[SettingsTemplateFile] | None = None

        if name == "library":
            return self.library

        if name == "collection":
            return self.collection

        if name == "metadata":
            return self.metadata

        if name == "overlay":
            return self.overlay
        
        raise ValueError("Unknown template group name: '{}".format(name))

    def getTemplateByGroupAndLibraryType(self, group: str, libraryType: SettingsTemplateLibraryTypeEnum | str ) -> List[SettingsTemplateFile] | None:
        if isinstance(libraryType, SettingsTemplateLibraryTypeEnum):
            libraryType = str(libraryType.value)

        templateGroupList = self.getTemplateByGroupName(group)

        #logging.getLogger("pmm_cfg_gen").debug("templateGroupList: {}".format(jsonpickle.dumps(templateGroupList, unpicklable=False)))

        strGroupLibrary = f"{group}.{libraryType}".lower().strip()
        strGroupAny = f"{group}.any".lower().strip()

        #logging.getLogger("pmm_cfg_gen").debug("strGroupLibrary: '{}'".format(strGroupLibrary))
        #logging.getLogger("pmm_cfg_gen").debug("strGroupAny: '{}'".format(strGroupAny))
        
        result = [x for x in templateGroupList if x.type.lower() == strGroupLibrary or x.type.lower() == strGroupAny]

        if result is not None and len(result) > 0:
            return result 
        
        # raise ValueError(
        #     "No template found for group '{}' and library type '{}'".format(
        #         group, libraryType
        #     )
        # )

        return None


class SettingsTheTvDatabase:
    apiKey: str | None
    pin: str | None

    def __init__(self, apiKey: str | None, pin: str | None) -> None:
        self.apiKey = apiKey
        self.pin = pin


class SettingsTheMovieDatabase:
    limitCollectionResults: int
    apiKey: str
    language: str
    region: str

    def __init__(self, limitCollectionResults: int, apiKey: str, language: str, region: str) -> None:
        self.limitCollectionResults = limitCollectionResults
        self.apiKey = apiKey
        self.language = language
        self.region = region


class SettingsThePosterDatabase:
    enablePro: bool
    searchUrlPro: str
    searchUrl: str
    dbAssetUrl: str

    def __init__(self, enablePro: bool, searchUrlPro: str, searchUrl: str, dbAssetUrl: str) -> None:
        self.enablePro = enablePro
        self.searchUrlPro = searchUrlPro
        self.searchUrl = searchUrl
        self.dbAssetUrl = dbAssetUrl


class SettingsRunTime:
    currentWorkingPath: str
    currentWorkingPathRelative: str

    def __init__(self, currentWorkingPath: str) -> None:
        self.currentWorkingPath = currentWorkingPath

class Settings:
    version: str
    plex: SettingsPlexServer
    plexMetaManager: SettingsPlexMetaManager
    thePosterDatabase: SettingsThePosterDatabase
    theMovieDatabase: SettingsTheMovieDatabase
    theTvDatabase: SettingsTheTvDatabase
    templates: SettingsTemplateGroups
    output: SettingsOutput
    generate: SettingsGenerate
    runtime: SettingsRunTime

    def __init__(self, version: str, plex: SettingsPlexServer, plexMetaManager: SettingsPlexMetaManager, thePosterDatabase: SettingsThePosterDatabase, theMovieDatabase: SettingsTheMovieDatabase,  theTvDatabase : SettingsTheTvDatabase, templates: SettingsTemplateGroups, output: SettingsOutput, generate: SettingsGenerate, runtime: SettingsRunTime) -> None:
        self.version = version
        self.plex = plex
        self.plexMetaManager = plexMetaManager
        self.thePosterDatabase = thePosterDatabase
        self.theMovieDatabase = theMovieDatabase
        self.theTvDatabase = theTvDatabase
        self.templates = templates
        self.output = output
        self.generate = generate
        self.runtime = runtime

#######################################################################

class SettingsManager:
    _config: confuse.Configuration
    settings: Settings
    modulePath: Path

    def __init__(self) -> None:
        self._logger = logging.getLogger("pmm_cfg_gen")
        self.modulePath = Path(str(importlib_resources.files("pmm_cfg_gen")))

    def loadFromFile(self, fileName: str, cmdLineArgs=None) -> None:
        self._logger.debug("Loading Configuration")

        self._config = confuse.Configuration("pmm_cfg_gen", "pmm_cfg_gen")

        self._logger.debug("Loading Configuration from Default Configuration")
        self._config._add_default_source()
        self._config._add_user_source()

        self._config.set_file(self.modulePath.joinpath("config_default.yaml"))

        if os.path.exists(fileName):
            self._logger.debug("Loading Configuration from User Configuration: '{}'".format(fileName))
            self._config.set_file(fileName)

        self._logger.debug("Loading Configuration from Environment")
        load_dotenv(Path(os.getcwd(), ".env"))
        self._config.set_env("PMMCFG")

        if cmdLineArgs is not None:
            self._logger.debug("Loading Configuration from Command Line")
            self._logger.debug("Command Line Args: {}".format(cmdLineArgs))
            self._config.set_args(cmdLineArgs, dots=True)

        self._config.set_redaction("plex.token", True)

        self._logger.debug(
            "Configuration Directory: {}".format(self._config.config_dir())
        )
        self._logger.debug(
            "User Configuration Path: {}".format(self._config.user_config_path())
        )

        self._logger.debug("Loaded Configuration:")
        self._logger.debug(jsonpickle.dumps(self._config, unpicklable=False))

        self.settings = Settings(
            version=self._config["version"].get(confuse.Optional(str)),  # type: ignore
            plex=SettingsPlexServer(
                serverUrl=expandvars(self._config["plex"]["serverUrl"].as_str()),
                token=expandvars(self._config["plex"]["token"].as_str()),
                libraries=self._config["plex"]["libraries"].get(confuse.Optional(list)),  # type: ignore
                pmmDefaults=SettingsPmmDefaults(
                    deltaOnly=self._config["pmm"]["deltaOnly"].get(confuse.Optional(bool, default=None)),  # type: ignore
                    basePath=self._config["pmm"]["basePath"].get(confuse.Optional(str, default=None)),  # type: ignore
                )
            ),
            thePosterDatabase=SettingsThePosterDatabase(
                searchUrl=expandvars(
                    self._config["thePosterDatabase"]["searchUrl"].as_str()
                ),
                searchUrlPro=expandvars(
                    self._config["thePosterDatabase"]["searchUrlPro"].as_str()
                ),
                dbAssetUrl=expandvars(
                    self._config["thePosterDatabase"]["dbAssetUrl"].as_str()
                ),
                enablePro=bool(
                    self._config["thePosterDatabase"]["enablePro"].get(bool)
                ),
            ),
            theMovieDatabase=SettingsTheMovieDatabase(
                apiKey=self._config["theMovieDatabase"]["apiKey"].get(confuse.Optional(None)),  # type: ignore
                language=self._config["theMovieDatabase"]["language"].get(confuse.Optional(None)),  # type: ignore
                region=self._config["theMovieDatabase"]["region"].get(confuse.Optional(None)),  # type: ignore
                limitCollectionResults=self._config["theMovieDatabase"]["limitCollectionResults"].get(confuse.Optional(None)),  # type: ignore
            ),
            theTvDatabase=SettingsTheTvDatabase(
                apiKey=self._config["theTvDatabase"]["apiKey"].get(confuse.Optional(None)),  # type: ignore
                pin=self._config["theTvDatabase"]["pin"].get(confuse.Optional(None)),  # type: ignore
            ),
            templates=SettingsTemplateGroups(
                collection=SettingsTemplateFile.from_list_dict(self._config["templates"]["collection"].get(confuse.Optional(list))),  # type: ignore
                library=SettingsTemplateFile.from_list_dict(self._config["templates"]["library"].get(confuse.Optional(list))),  # type: ignore
                metadata=SettingsTemplateFile.from_list_dict(self._config["templates"]["metadata"].get(confuse.Optional(list))),  # type: ignore
                overlay=SettingsTemplateFile.from_list_dict(self._config["templates"]["overlay"].get(confuse.Optional(list))),  # type: ignore
                templatePath=self._config["templates"]["templatePath"].get(confuse.Optional(list)),  # type: ignore
            ),
            output=SettingsOutput(
                path=str(self._config["output"]["path"].as_str()),
                pathFormat=str(self._config["output"]["pathFormat"].as_str()),
                sharedTemplatePathFormat=str(self._config["output"]["sharedTemplatePathFormat"].as_str()),
                overwrite=bool(self._config["output"]["overwrite"].get(confuse.Optional(False))),
                fileNameFormat=SettingsOutputFileNames(
                    library=str(
                        self._config["output"]["fileNameFormat"]["library"].get(
                            confuse.Optional("{{library.title}}")
                        )
                    ),
                    collections=str(
                        self._config["output"]["fileNameFormat"]["collections"].get(
                            confuse.Optional("{{collection.title}} ({{collection.year}})")
                        )
                    ),
                    metadata=str(
                        self._config["output"]["fileNameFormat"]["metadata"].get(
                            confuse.Optional("{{item.title}} ({{item.year}}) [{{item.editionTitle}}]")
                        )
                    ),
                    libraryReport=str(
                        self._config["output"]["fileNameFormat"]["libraryReport"].get(
                            confuse.Optional("{{library.title}} - Library")
                        )
                    ),
                    collectionsReport=str(
                        self._config["output"]["fileNameFormat"]["collectionsReport"].get(
                            confuse.Optional("{{library.title}} - Collections")
                        )
                    ),
                    metadataReport=str(
                        self._config["output"]["fileNameFormat"]["metedataReport"].get(
                            confuse.Optional("{{library.title}} - Items")
                        )
                    ),
                    report=str(self._config["output"]["fileNameFormat"]["report"].get(confuse.Optional("{{library.title}} -Report"))),
                    template=str(self._config["output"]["fileNameFormat"]["template"].get(confuse.Optional("template"))),
                )
            ),
            generate=SettingsGenerate(
                types=self._config["generate"]["types"].get(confuse.Optional(list)),  # type: ignore
                formats=self._config["generate"]["formats"].get(confuse.Optional(list)),  # type: ignore
            ),
            plexMetaManager=SettingsPlexMetaManager.from_dict(self._config["plexMetaManager"].get(confuse.Optional(dict))),  # type: ignore
            runtime=SettingsRunTime(
                currentWorkingPath=os.path.curdir
            ),
        )

        self._logger.debug("Active Settings:")
        self._logger.debug(jsonpickle.dumps(self.settings, unpicklable=False))


#######################################################################

globalSettingsMgr = SettingsManager()
