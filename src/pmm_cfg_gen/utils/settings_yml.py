#!/usr/bin/env python3

#######################################################################

from typing import List
from pathlib import Path
from expandvars import expandvars
from dotenv import load_dotenv
import os
import confuse
import logging 
import jsonpickle
import importlib_resources

#######################################################################
class SettingsOutput():
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
    pmmFileName: str | None
    jsonFileName: str | None

    def __init__(self, pmmFileName: str | None, jsonFileName: str | None) -> None:
        
        self.pmmFileName = pmmFileName
        self.jsonFileName = jsonFileName

class SettingsTemplateFileGroup:
    movies: SettingsTemplateFiles | None
    shows: SettingsTemplateFiles | None
    library: SettingsTemplateFiles | None

    def __init__(self, movies: SettingsTemplateFiles | None, shows: SettingsTemplateFiles | None, library: SettingsTemplateFiles | None = None) -> None:
        
        self.movies = movies
        self.shows = shows
        self.library = library

    def getByItemType(self, itemType: str) -> SettingsTemplateFiles:
        if itemType.lower() == "movie" and self.movies is not None: return self.movies
        if itemType.lower() == "show" and self.shows is not None: return self.shows
        if itemType.lower() == "library" and self.library is not None: return self.library
        
        raise BaseException("Unknown item type or template not defined: {}".format(itemType))

class SettingsTemplates:
    templatePath: str | None
    collections: SettingsTemplateFileGroup
    metadata: SettingsTemplateFileGroup

    def __init__(self, collections: SettingsTemplateFileGroup, metadata: SettingsTemplateFileGroup, templatePath : str | None = None) -> None:
        
        self.templatePath = templatePath
        self.collections = collections
        self.metadata = metadata

    def getTemplateRootPath(self) -> Path:
        if self.templatePath is None or self.templatePath == "pmm_cfg_gen.tempaltes":
            self.templatePath = str(importlib_resources.files("pmm_cfg_gen").joinpath("templates"))
            
        return Path(self.templatePath).resolve()

class SettingsThePosterDatabase:
    searchUrl: str
    dbAssetUrl: str

    def __init__(self, searchUrl: str, dbAssetUrl: str) -> None:
                
        self.searchUrl = searchUrl
        self.dbAssetUrl = dbAssetUrl

class SettingsGenerate:
    enableJson: bool
    enablePmm: bool

    def __init__(self, enableJson: bool, enablePmm : bool) -> None:
        self.enableJson = enableJson
        self.enablePmm = enablePmm

class Settings:
    plex: SettingsPlex
    thePosterDatabase: SettingsThePosterDatabase
    templates: SettingsTemplates
    output: SettingsOutput
    generate : SettingsGenerate

    def __init__(self, plex: SettingsPlex, thePosterDatabase: SettingsThePosterDatabase, templates: SettingsTemplates, output: SettingsOutput, generate : SettingsGenerate) -> None:
        
        self.plex = plex
        self.thePosterDatabase = thePosterDatabase
        self.templates = templates
        self.output = output
        self.generate = generate

#######################################################################

class SettingsManager:
    _config : confuse.Configuration
    settings : Settings 
    
    def __init__(self) -> None:
        self._logger = logging.getLogger("pmm_cfg_gen")

    def loadFromFile(self, fileName: str, cmdLineArgs = None) -> None:
        self._logger.debug("Loading Configuration")

        self._config = confuse.Configuration("pmm_cfg_gen", "pmm_cfg_gen")

        self._logger.debug("Loading Configuration from Default Configuration")
        self._config._add_default_source()
        self._config._add_user_source()

        self._config.set_file(importlib_resources.files("pmm_cfg_gen").joinpath("config_default.yaml"))

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

        self._logger.debug(self._config.dump())
        self._logger.info("Configuration Directory: {}".format(self._config.config_dir()))
        self._logger.info("User Configuration Path: {}".format(self._config.user_config_path()))

        self.settings = Settings(
            plex=SettingsPlex(
                serverUrl=expandvars(self._config['plex']['serverUrl'].as_str()),
                token=expandvars(self._config['plex']['token'].as_str()),
                libraries=self._config['plex']['libraries'].get(confuse.Optional(list)) # type: ignore
            ),
            thePosterDatabase=SettingsThePosterDatabase(
                searchUrl=expandvars(self._config['thePosterDatabase']['searchUrl'].as_str()),
                dbAssetUrl=expandvars(self._config['thePosterDatabase']['dbAssetUrl'].as_str())
            ),
            templates=SettingsTemplates(
                collections=SettingsTemplateFileGroup(
                    movies=SettingsTemplateFiles(
                        pmmFileName=str(self._config['templates']['collections']['movies']['pmmFileName'].as_str()),
                        jsonFileName=str(self._config['templates']['collections']['movies']['jsonFileName'].as_str())
                    ),
                    shows=SettingsTemplateFiles(
                        pmmFileName=str(self._config['templates']['collections']['shows']['pmmFileName'].as_str()),
                        jsonFileName=str(self._config['templates']['collections']['shows']['jsonFileName'].as_str())
                    )
                ),
                metadata=SettingsTemplateFileGroup(
                    movies=SettingsTemplateFiles(
                        pmmFileName=str(self._config['templates']['metadata']['movies']['pmmFileName'].as_str()),
                        jsonFileName=str(self._config['templates']['metadata']['movies']['jsonFileName'].as_str())
                    ),
                    shows=SettingsTemplateFiles(
                        pmmFileName=str(self._config['templates']['metadata']['shows']['pmmFileName'].as_str()),
                        jsonFileName=str(self._config['templates']['metadata']['shows']['jsonFileName'].as_str())
                    ), 
                    library=SettingsTemplateFiles(
                        pmmFileName=str(self._config['templates']['metadata']['library']['pmmFileName'].get(confuse.Optional(None))),
                        jsonFileName=str(self._config['templates']['metadata']['library']['jsonFileName'].get(confuse.Optional(None)))
                    )
                )
            ),
            output=SettingsOutput(
                path=str(self._config['output']['path'].as_str()),
                pathFormat=str(self._config['output']['pathFormat'].as_str())
            ),
            generate=SettingsGenerate(
                enableJson=self._config['generate']['enableJson'].get(confuse.Optional(False)), # type: ignore
                enablePmm=self._config['generate']['enableJson'].get(confuse.Optional(True)) # type: ignore
            )
        )

#######################################################################

globalSettingsMgr = SettingsManager()