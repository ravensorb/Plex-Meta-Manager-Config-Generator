#!/usr/bin/env python3

#######################################################################

import logging
import os
from pathlib import Path
from typing import List

import confuse
import importlib_resources
import jsonpickle
from dotenv import load_dotenv
from expandvars import expandvars


#######################################################################
class SettingsOutputFileNames:
    collections: str
    metadata: str
    collectionsReport: str
    metadataReport : str

    def __init__(self, collections: str, metadata: str, collectionsReport: str, metadataReport: str) -> None:
        self.collections = collections
        self.metadata = metadata
        self.collectionsReport = collectionsReport
        self.metadataReport = metadataReport

class SettingsOutput:
    path: str
    pathFormat: str
    fileNameFormat = SettingsOutputFileNames

    def __init__(
        self,
        path: str,
        pathFormat: str,
        fileNameFormat: SettingsOutputFileNames
    ) -> None:
        self.path = path
        self.pathFormat = pathFormat
        self.fileNameFormat = fileNameFormat

class SettingsPlex:
    serverUrl: str
    token: str
    libraries: List[str]

    def __init__(self, serverUrl: str, token: str, libraries: List[str]) -> None:
        self.serverUrl = serverUrl
        self.token = token
        self.libraries = libraries


class SettingsTemplateFiles:
    yamlFileName: str | None
    jsonFileName: str | None
    htmlFileName: str | None

    def __init__(
        self,
        yamlFileName: str | None,
        jsonFileName: str | None,
        htmlFileName: str | None = None,
    ) -> None:
        self.yamlFileName = yamlFileName
        self.jsonFileName = jsonFileName
        self.htmlFileName = htmlFileName


class SettingsTemplatePlexItemFileGroup:
    movies: SettingsTemplateFiles | None
    shows: SettingsTemplateFiles | None
    library: SettingsTemplateFiles | None

    def __init__(
        self,
        movies: SettingsTemplateFiles | None,
        shows: SettingsTemplateFiles | None,
        library: SettingsTemplateFiles | None = None,
    ) -> None:
        self.movies = movies
        self.shows = shows
        self.library = library

    def getByItemType(self, itemType: str) -> SettingsTemplateFiles:
        if itemType.lower() == "movie" and self.movies is not None:
            return self.movies
        if itemType.lower() == "show" and self.shows is not None:
            return self.shows
        if itemType.lower() == "library" and self.library is not None:
            return self.library

        raise BaseException(
            "Unknown item type or template not defined: {}".format(itemType)
        )


class SettingsTemplateReportFileGroup:
    collection: SettingsTemplateFiles | None
    metadata: SettingsTemplateFiles | None

    def __init__(
        self,
        collection: SettingsTemplateFiles | None,
        metadata: SettingsTemplateFiles | None,
    ) -> None:
        self.collection = collection
        self.metadata = metadata


class SettingsTemplates:
    templatePath: str | None
    collections: SettingsTemplatePlexItemFileGroup
    metadata: SettingsTemplatePlexItemFileGroup
    reports: SettingsTemplateReportFileGroup

    def __init__(
        self,
        collections: SettingsTemplatePlexItemFileGroup,
        metadata: SettingsTemplatePlexItemFileGroup,
        reports: SettingsTemplateReportFileGroup,
        templatePath: str | None = None,
    ) -> None:
        self.templatePath = templatePath
        self.collections = collections
        self.metadata = metadata
        self.reports = reports

    def getTemplateRootPath(self) -> Path:
        if self.templatePath is None or self.templatePath == "pmm_cfg_gen.tempaltes":
            self.templatePath = str(
                importlib_resources.files("pmm_cfg_gen").joinpath("templates")
            )

        return Path(self.templatePath).resolve()


class SettingsThePosterDatabase:
    enablePro: bool
    searchUrlPro: str
    searchUrl: str
    dbAssetUrl: str

    def __init__(
        self, searchUrl: str, searchUrlPro: str, dbAssetUrl: str, enablePro: bool
    ) -> None:
        self.searchUrl = searchUrl
        self.searchUrlPro = searchUrlPro
        self.dbAssetUrl = dbAssetUrl
        self.enablePro = enablePro


class SettingsTheMovieDatabase:
    apiKey: str | None
    language: str | None
    region: str | None
    limitCollectionResults: int | None

    def __init__(
        self,
        apiKey: str | None,
        language: str | None,
        region: str | None,
        limitCollectionResults: int | None,
    ) -> None:
        self.apiKey = apiKey
        self.language = language
        self.region = region
        self.limitCollectionResults = limitCollectionResults


class SettingsTheTvDatabase:
    apiKey: str | None
    pin: str | None

    def __init__(self, apiKey: str | None, pin: str | None) -> None:
        self.apiKey = apiKey
        self.pin = pin


class SettingsGenerate:
    enableJson: bool
    enableYaml: bool
    enableHtml: bool
    enableItemReport: bool

    def __init__(
        self,
        enableJson: bool,
        enableYaml: bool,
        enableHtml: bool,
        enableItemReport: bool,
    ) -> None:
        self.enableJson = enableJson
        self.enableYaml = enableYaml
        self.enableHtml = enableHtml
        self.enableItemReport = enableItemReport


class Settings:
    plex: SettingsPlex
    thePosterDatabase: SettingsThePosterDatabase
    theMovieDatabase: SettingsTheMovieDatabase
    theTvDatabase: SettingsTheTvDatabase
    templates: SettingsTemplates
    output: SettingsOutput
    generate: SettingsGenerate

    def __init__(
        self,
        plex: SettingsPlex,
        thePosterDatabase: SettingsThePosterDatabase,
        theMovieDatabase: SettingsTheMovieDatabase,
        theTvDatabase: SettingsTheTvDatabase,
        templates: SettingsTemplates,
        output: SettingsOutput,
        generate: SettingsGenerate,
    ) -> None:
        self.plex = plex
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
            plex=SettingsPlex(
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
            templates=SettingsTemplates(
                collections=SettingsTemplatePlexItemFileGroup(
                    movies=SettingsTemplateFiles(
                        yamlFileName=str(
                            self._config["templates"]["collections"]["movies"][
                                "yamlFileName"
                            ].as_str()
                        ),
                        jsonFileName=str(
                            self._config["templates"]["collections"]["movies"][
                                "jsonFileName"
                            ].as_str()
                        ),
                    ),
                    shows=SettingsTemplateFiles(
                        yamlFileName=str(
                            self._config["templates"]["collections"]["shows"][
                                "yamlFileName"
                            ].as_str()
                        ),
                        jsonFileName=str(
                            self._config["templates"]["collections"]["shows"][
                                "jsonFileName"
                            ].as_str()
                        ),
                    ),
                ),
                metadata=SettingsTemplatePlexItemFileGroup(
                    movies=SettingsTemplateFiles(
                        yamlFileName=str(
                            self._config["templates"]["metadata"]["movies"][
                                "yamlFileName"
                            ].as_str()
                        ),
                        jsonFileName=str(
                            self._config["templates"]["metadata"]["movies"][
                                "jsonFileName"
                            ].as_str()
                        ),
                    ),
                    shows=SettingsTemplateFiles(
                        yamlFileName=str(
                            self._config["templates"]["metadata"]["shows"][
                                "yamlFileName"
                            ].as_str()
                        ),
                        jsonFileName=str(
                            self._config["templates"]["metadata"]["shows"][
                                "jsonFileName"
                            ].as_str()
                        ),
                    ),
                    library=SettingsTemplateFiles(
                        yamlFileName=str(
                            self._config["templates"]["metadata"]["library"][
                                "yamlFileName"
                            ].get(confuse.Optional(None))
                        ),
                        jsonFileName=str(
                            self._config["templates"]["metadata"]["library"][
                                "jsonFileName"
                            ].get(confuse.Optional(None))
                        ),
                    ),
                ),
                reports=SettingsTemplateReportFileGroup(
                    collection=SettingsTemplateFiles(
                        yamlFileName=str(
                            self._config["templates"]["reports"]["collection"][
                                "yamlFileName"
                            ].get(confuse.Optional(None))
                        ),
                        jsonFileName=str(
                            self._config["templates"]["reports"]["collection"][
                                "jsonFileName"
                            ].get(confuse.Optional(None))
                        ),
                        htmlFileName=str(
                            self._config["templates"]["reports"]["collection"][
                                "htmlFileName"
                            ].get(confuse.Optional(None))
                        ),
                    ),
                    metadata=SettingsTemplateFiles(
                        yamlFileName=str(
                            self._config["templates"]["reports"]["metadata"][
                                "yamlFileName"
                            ].get(confuse.Optional(None))
                        ),
                        jsonFileName=str(
                            self._config["templates"]["reports"]["metadata"][
                                "jsonFileName"
                            ].get(confuse.Optional(None))
                        ),
                        htmlFileName=str(
                            self._config["templates"]["reports"]["metadata"][
                                "htmlFileName"
                            ].get(confuse.Optional(None))
                        ),
                    ),
                ),
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
                enableHtml=self._config["generate"]["enableHtml"].get(confuse.Optional(False)),  # type: ignore
                enableJson=self._config["generate"]["enableJson"].get(confuse.Optional(False)),  # type: ignore
                enableYaml=self._config["generate"]["enableYaml"].get(confuse.Optional(True)),  # type: ignore
                enableItemReport=self._config["generate"]["enableItemReport"].get(confuse.Optional(True)),  # type: ignore
            ),
        )

        self._logger.debug("Active Settings:")
        self._logger.debug(jsonpickle.dumps(self.settings, unpicklable=False))


#######################################################################

globalSettingsMgr = SettingsManager()
