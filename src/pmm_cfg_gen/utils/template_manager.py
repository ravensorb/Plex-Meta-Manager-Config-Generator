#!/usr/bin/env python3
#######################################################################

import json
import logging
import urllib.parse
from pathlib import Path

import jinja2
import jinja2.exceptions
import jsonpickle
import requests

from pmm_cfg_gen.utils.fileutils import writeFile
from pmm_cfg_gen.utils.plex_utils import isPMMItem, PlexItemHelper
from pmm_cfg_gen.utils.settings_yml import globalSettingsMgr

#######################################################################
# Jinja2 filters and utilitiy methods


def itemToJson(item):
    str = jsonpickle.encode(item, unpicklable=False)

    return str

def formatJson(data):
    return jsonpickle.dumps(data, indent=4, unpicklable=False)

def generateTpDbSearchUrl(item, baseUrl = None) -> str:
    if baseUrl is None:
        baseUrl = globalSettingsMgr.settings.thePosterDatabase.searchUrlPro if globalSettingsMgr.settings.thePosterDatabase.enablePro else globalSettingsMgr.settings.thePosterDatabase.searchUrl

    urlParms = {}

    urlParms.update({"term": item.title})

    if globalSettingsMgr.settings.thePosterDatabase.enablePro:
        if item.type == "collection":
            if item.subtype == "movie":
                urlParms.update({"category": "Movies"})
            elif item.subtype == "show":
                urlParms.update({"category": "Shows"})
        elif item.type == "movie":
            urlParms.update({"category": "Movies"})
            urlParms.update({"year_filter": "equals"})
            urlParms.update({"yone": item.year})
        elif item.type == "show":
            urlParms.update({"category": "Shows"})
            urlParms.update({"year_filter": "equals"})
            urlParms.update({"yone": item.year})
        elif item.type == "season":
            urlParms.update({"category": "Shows"})
            urlParms.update({"term": "{} {}".format(item.parentTitle, item.title)})

        if "guids" in item.__dict__:
            ids = dict(o.id.split("://") for o in item.guids)

            if "tmdb" in ids.keys():
                urlParms.update({"tmdb_id": ids["tmdb"]})
            if "imdb" in ids.keys():
                urlParms.update({"imdb_id": ids["imdb"]})
            if "tvdb" in ids.keys():
                urlParms.update({"tvdb_id": ids["tvdb"]})

    #logging.getLogger("pmm-cfg-gen").info(urlParms)
    
    urlQS = urllib.parse.urlencode(urlParms)

    req = requests.PreparedRequest()
    req.prepare_url(baseUrl, urlQS)

    return str(req.url)

def getItemGuidByName(item, guidName : str) -> str | None: 
    plexItem = PlexItemHelper(item)

    return plexItem.getGuidByName(guidName)
    
#######################################################################

class TemplateManager:
    __tplEnv: jinja2.Environment
    __cachedTemplates: dict

    #######################################################################
    def __init__(self, templatePath: str | Path) -> None:
        self._logger = logging.getLogger("pmm_cfg_gen")

        self._logger.debug(
            "Initializing Template Environment.  Template Path: '{}'".format(
                templatePath
            )
        )

        self.__tplEnv = jinja2.Environment(loader=jinja2.FileSystemLoader(templatePath))

        self.__cachedTemplates = {}
        self.__registerFilters()

    def render(self, templateName: str | Path, tplArgs: dict) -> str | None:
        self._logger.debug("Render data using template '{}'".format(templateName))

        tpl = self.__getTemplate(templateName)

        if tpl is None:
            self._logger.warn("Template Does not exist: '{}'".format(templateName))

            return None

        if "settings" not in tplArgs.keys():
            tplArgs.update({"settings": globalSettingsMgr.settings})

        # self._logger.info("tplArgs: {}".format(tplArgs))
        return tpl.render(tplArgs)

    def renderAndSave(
        self, templateName: str | Path, fileName: str | Path, tplArgs: dict
    ):
        if templateName is None or templateName == "None":
            return

        self._logger.debug(
            "Render data using template '{}' and save to '{}'".format(
                templateName, fileName
            )
        )

        tplResult = self.render(templateName, tplArgs)

        if tplResult is not None:
            writeFile(fileName, tplResult)

    #######################################################################
    def __getTemplate(self, templateName: str | Path) -> jinja2.Template | None:
        if not templateName in self.__cachedTemplates.keys():
            self._logger.debug("Loading template into cache: {}".format(templateName))

            try:
                tpl = self.__tplEnv.get_template(str(templateName))

                self.__cachedTemplates[templateName] = tpl
            except (jinja2.TemplateSyntaxError, jinja2.exceptions.UndefinedError) as exTpl:
                self._logger.error("Failed to load template: '{}'. Exception: {}".format(templateName, str(exTpl)))
                if self._logger.isEnabledFor(logging.DEBUG):
                    self._logger.exception("Template Syntax Error: '{}'".format(templateName))
            except:
                if self._logger.isEnabledFor(logging.DEBUG):
                    self._logger.exception("Failed to load template: '{}'".format(templateName))

                return None

        else:
            self._logger.debug(
                "Retrieving template from cache: {}".format(templateName)
            )

        return self.__cachedTemplates[templateName]

    def __registerFilters(self):
        self.__tplEnv.filters["plexToJson"] = itemToJson
        self.__tplEnv.filters["isPMMItem"] = isPMMItem
        self.__tplEnv.filters["formatJson"] = formatJson
        self.__tplEnv.filters["generateTpDbSearchUrl"] = generateTpDbSearchUrl
        self.__tplEnv.filters["getItemGuidByName"] = getItemGuidByName
