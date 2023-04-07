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
class SettingsOutput:
    path: str
    pathFormat: str

    def __init__(self, path: str, pathFormat: str) -> None:
        self.path = path
        self.pathFormat = pathFormat


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


class SettingsTemplateFileGroup:
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


class SettingsTemplates:
    templatePath: str | None
    collections: SettingsTemplateFileGroup
    metadata: SettingsTemplateFileGroup
    thePosterDatabase: SettingsTemplateFiles | None

    def __init__(
        self,
        collections: SettingsTemplateFileGroup,
        metadata: SettingsTemplateFileGroup,
        templatePath: str | None = None,
        thePosterDatabase: SettingsTemplateFiles | None = None,
    ) -> None:
        self.templatePath = templatePath
        self.collections = collections
        self.metadata = metadata
        self.thePosterDatabase = thePosterDatabase

    def getTemplateRootPath(self) -> Path:
        if self.templatePath is None or self.templatePath == "pmm_cfg_gen.tempaltes":
            self.templatePath = str(
                importlib_resources.files("pmm_cfg_gen").joinpath("templates")
            )

        return Path(self.templatePath).resolve()


class SettingsThePosterDatabase:
    baseFileName: str
    searchUrl: str
    dbAssetUrl: str

    def __init__(self, searchUrl: str, dbAssetUrl: str, baseFileName: str) -> None:
        self.searchUrl = searchUrl
        self.dbAssetUrl = dbAssetUrl
        self.baseFileName = baseFileName


class SettingsGenerate:
    enableJson: bool
    enableYaml: bool
    enableHtml: bool
    enaleThePosterDb: bool

    def __init__(
        self,
        enableJson: bool,
        enableYaml: bool,
        enableHtml: bool,
        enableThePosterDb: bool,
    ) -> None:
        self.enableJson = enableJson
        self.enableYaml = enableYaml
        self.enableHtml = enableHtml
        self.enaleThePosterDb = enableThePosterDb


class Settings:
    plex: SettingsPlex
    thePosterDatabase: SettingsThePosterDatabase
    templates: SettingsTemplates
    output: SettingsOutput
    generate: SettingsGenerate

    def __init__(
        self,
        plex: SettingsPlex,
        thePosterDatabase: SettingsThePosterDatabase,
        templates: SettingsTemplates,
        output: SettingsOutput,
        generate: SettingsGenerate,
    ) -> None:
        self.plex = plex
        self.thePosterDatabase = thePosterDatabase
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
        load_dotenv()
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
                dbAssetUrl=expandvars(
                    self._config["thePosterDatabase"]["dbAssetUrl"].as_str()
                ),
                baseFileName=str(
                    self._config["thePosterDatabase"]["baseFileName"].get(
                        confuse.Optional("thePosterDatabase")
                    )
                ),
            ),
            templates=SettingsTemplates(
                collections=SettingsTemplateFileGroup(
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
                metadata=SettingsTemplateFileGroup(
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
                thePosterDatabase=SettingsTemplateFiles(
                    yamlFileName=str(
                        self._config["templates"]["thePosterDatabase"][
                            "yamlFileName"
                        ].get(confuse.Optional(None))
                    ),
                    jsonFileName=str(
                        self._config["templates"]["thePosterDatabase"][
                            "jsonFileName"
                        ].get(confuse.Optional(None))
                    ),
                    htmlFileName=str(
                        self._config["templates"]["thePosterDatabase"][
                            "htmlFileName"
                        ].get(confuse.Optional(None))
                    ),
                ),
            ),
            output=SettingsOutput(
                path=str(self._config["output"]["path"].as_str()),
                pathFormat=str(self._config["output"]["pathFormat"].as_str()),
            ),
            generate=SettingsGenerate(
                enableHtml=self._config["generate"]["enableHtml"].get(confuse.Optional(False)),  # type: ignore
                enableJson=self._config["generate"]["enableJson"].get(confuse.Optional(False)),  # type: ignore
                enableYaml=self._config["generate"]["enableYaml"].get(confuse.Optional(True)),  # type: ignore
                enableThePosterDb=self._config["generate"]["enableThePosterDb"].get(confuse.Optional(True)),  # type: ignore
            ),
        )

        self._logger.debug("Active Settings:")
        self._logger.debug(jsonpickle.dumps(self.settings, unpicklable=False))


#######################################################################

globalSettingsMgr = SettingsManager()
