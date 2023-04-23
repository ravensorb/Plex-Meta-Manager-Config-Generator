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
    MOVIE = "movie"
    MUSIC = "music"
    REPORT = "report"
    SHOW = "show"
    COLLECTION_REPORT = "collection.report"
    MOVIE_REPORT = "movie.report"
    MUSIC_REPORT = "music.report"


class SettingsGenerate:
    enableJson: bool
    enableYaml: bool
    enableHtml: bool
    types: list[str]
    formats: list[str]

    def __init__(self, enableJson: bool, enableYaml: bool, enableHtml: bool, types: list[str], formats: list[str]) -> None:
        self.enableJson = enableJson
        self.enableYaml = enableYaml
        self.enableHtml = enableHtml
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
    collections: str
    metadata: str
    collectionsReport: str
    metadataReport: str

    def __init__(self, collections: str, metadata: str, collectionsReport: str, metadataReport: str) -> None:
        self.collections = collections
        self.metadata = metadata
        self.collectionsReport = collectionsReport
        self.metadataReport = metadataReport


class SettingsOutput:
    path: str
    pathFormat: str
    fileNameFormat: SettingsOutputFileNames

    def __init__(self, path: str, pathFormat: str, fileNameFormat: SettingsOutputFileNames) -> None:
        self.path = path
        self.pathFormat = pathFormat
        self.fileNameFormat = fileNameFormat


class SettingsPlexServer:
    serverUrl: str
    token: str
    libraries: List[str]

    def __init__(self, serverUrl: str, token: str, libraries: List[str]) -> None:
        self.serverUrl = serverUrl
        self.token = token
        self.libraries = libraries


class SettingsPlexMetaManagerFolder:
    library: str
    path: str

    def __init__(self, library: str, path: str) -> None:
        self.library = library
        self.path = path

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            data["library"],
            data["path"]
        )


class SettingsPlexMetaManager:
    cacheExistingFiles: bool
    folders: List[SettingsPlexMetaManagerFolder]

    def __init__(self, cacheExistingFiles: bool, folders: List[SettingsPlexMetaManagerFolder]) -> None:
        self.cacheExistingFiles = cacheExistingFiles
        self.folders = folders

    def getFolderByLibraryName(self, libraryName: str) -> SettingsPlexMetaManagerFolder | None:
        result = next((x for x in self.folders if x.library.strip() == libraryName.strip()), None)

        return result

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            data["cacheExistingFiles"],
            [SettingsPlexMetaManagerFolder.from_dict(x) for x in data["folders"]]
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

    def getTemplateByGroupAndLibraryType(
        self, group: str, libraryType: SettingsTemplateLibraryTypeEnum | str
    ) -> List[SettingsTemplateFile] | None:
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
        
        raise ValueError(
            "No template found for group '{}' and library type '{}'".format(
                group, libraryType
            )
        )


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


class Settings:
    plex: SettingsPlexServer
    plexMetaManager: SettingsPlexMetaManager
    thePosterDatabase: SettingsThePosterDatabase
    theMovieDatabase: SettingsTheMovieDatabase
    theTvDatabase: SettingsTheTvDatabase
    templates: SettingsTemplateGroups
    output: SettingsOutput
    generate: SettingsGenerate

    def __init__(self, plex: SettingsPlexServer, plexMetaManager: SettingsPlexMetaManager, thePosterDatabase: SettingsThePosterDatabase, theMovieDatabase: SettingsTheMovieDatabase,  theTvDatabase : SettingsTheTvDatabase, templates: SettingsTemplateGroups, output: SettingsOutput, generate: SettingsGenerate) -> None:
        self.plex = plex
        self.plexMetaManager = plexMetaManager
        self.thePosterDatabase = thePosterDatabase
        self.theMovieDatabase = theMovieDatabase
        self.theTvDatabase = theTvDatabase
        self.templates = templates
        self.output = output
        self.generate = generate

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
            self._logger.debug("Loading Configuration from User Configuration")
            self._config.set_file(fileName)

        self._logger.debug("Loading Configuration from Environment")
        load_dotenv(Path(os.getcwd(), ".env"))
        self._config.set_env("PMMCFG")

        if cmdLineArgs is not None:
            self._logger.debug("Loading Configuration from Command Line")
            self._config.set_args(cmdLineArgs, dots=True)

        self._config.set_redaction("plex.token", True)

        self._logger.debug(
            "Configuration Directory: {}".format(self._config.config_dir())
        )
        self._logger.debug(
            "User Configuration Path: {}".format(self._config.user_config_path())
        )

        self.settings = Settings(
            plex=SettingsPlexServer(
                serverUrl=expandvars(self._config["plex"]["serverUrl"].as_str()),
                token=expandvars(self._config["plex"]["token"].as_str()),
                libraries=self._config["plex"]["libraries"].get(confuse.Optional(list)),  # type: ignore
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
                    self._config["thePosterDatabase"]["enablePro"].get(
                        confuse.Optional(False)
                    )
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
                fileNameFormat=SettingsOutputFileNames(
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
                )
            ),
            generate=SettingsGenerate(
                types=self._config["generate"]["types"].get(confuse.Optional(list)),  # type: ignore
                formats=self._config["generate"]["formats"].get(confuse.Optional(list)),  # type: ignore
                enableHtml=self._config["generate"]["enableHtml"].get(confuse.Optional(False)),  # type: ignore
                enableJson=self._config["generate"]["enableJson"].get(confuse.Optional(False)),  # type: ignore
                enableYaml=self._config["generate"]["enableYaml"].get(confuse.Optional(True)),  # type: ignore
            ),
            plexMetaManager=SettingsPlexMetaManager.from_dict(self._config["plexMetaManager"].get(confuse.Optional(dict))),  # type: ignore
        )

        self._logger.debug("Active Settings:")
        self._logger.debug(jsonpickle.dumps(self.settings, unpicklable=False))


#######################################################################

globalSettingsMgr = SettingsManager()
