#!/usr/bin/env python3
#######################################################################

import json
import logging
import urllib.parse
from pathlib import Path

import jinja2
import jsonpickle
import requests

from pmm_cfg_gen.utils.fileutils import writeFile
from pmm_cfg_gen.utils.plexutils import isPMMItem
from pmm_cfg_gen.utils.settings_yml import globalSettingsMgr

#######################################################################
# Jinja2 filters and utilitiy methods


def plexToJson(item):
    str = jsonpickle.encode(item, unpicklable=False)

    return str


def formatJson(str):
    return json.dumps(json.loads(str), indent=4)


def generateTpDbUrl(item, baseUrl=None) -> str:
    if baseUrl is None:
        baseUrl = globalSettingsMgr.settings.thePosterDatabase.searchUrl

    urlParms = {}

    if item.type == "movie":
        urlParms.update({"category": "Movies"})
        urlParms.update({"term": item.title})
        urlParms.update({"year_filter": "equals"})
        urlParms.update({"yone": item.year})

    if item.type == "show":
        urlParms.update({"category": "Shows"})
        urlParms.update({"term": item.title})
        urlParms.update({"year_filter": "equals"})
        urlParms.update({"yone": item.year})

    if item.type == "season":
        urlParms.update({"category": "Shows"})
        urlParms.update({"term": "{} {}".format(item.title, item.parentTitle)})

    if "guids" in item.__dict__:
        ids = dict(o.id.split("://") for o in item.guids)

        if "tmdb" in ids.keys():
            urlParms.update({"tmdb_id": ids["tmdb"]})
        if "imdb" in ids.keys():
            urlParms.update({"imdb_id": ids["imdb"]})
        if "tvdb" in ids.keys():
            urlParms.update({"tvdb_id": ids["tvdb"]})

    urlQS = urllib.parse.urlencode(urlParms)

    req = requests.PreparedRequest()
    req.prepare_url(baseUrl, urlQS)

    return str(req.url)


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

    def render(self, templateName: str | Path, tplArgs: dict) -> str:
        self._logger.debug("Render data using template '{}'".format(templateName))

        tpl = self.__getTemplate(templateName)

        if "settings" not in tplArgs.keys():
            tplArgs.update({"settings": globalSettingsMgr.settings})

        # self._logger.info("tplArgs: {}".format(tplArgs))
        return tpl.render(tplArgs)

    def renderAndSave(
        self, templateName: str | Path, fileName: str | Path, tplArgs: dict
    ):
        self._logger.debug(
            "Render data using template '{}' and save to '{}'".format(
                templateName, fileName
            )
        )

        tplResult = self.render(templateName, tplArgs)

        writeFile(fileName, tplResult)

    #######################################################################
    def __getTemplate(self, templateName: str | Path):
        if not templateName in self.__cachedTemplates.keys():
            self._logger.debug("Loading template into cache: {}".format(templateName))

            tpl = self.__tplEnv.get_template(str(templateName))

            self.__cachedTemplates[templateName] = tpl
        else:
            self._logger.debug(
                "Retrieving template from cache: {}".format(templateName)
            )

        return self.__cachedTemplates[templateName]

    def __registerFilters(self):
        self.__tplEnv.filters["plexToJson"] = plexToJson
        self.__tplEnv.filters["isPMMItem"] = isPMMItem
        self.__tplEnv.filters["formatJson"] = formatJson
        self.__tplEnv.filters["generateTpDbUrl"] = generateTpDbUrl
