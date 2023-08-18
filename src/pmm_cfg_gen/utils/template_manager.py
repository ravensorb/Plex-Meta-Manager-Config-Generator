#!/usr/bin/env python3
#######################################################################

import logging
from pathlib import Path

import jinja2
import jinja2.exceptions

from pmm_cfg_gen.utils.settings_utils_v1 import globalSettingsMgr
from pmm_cfg_gen.utils.file_utils import writeFile
from pmm_cfg_gen.utils.plex_utils import PlexItemHelper, PlexVideoHelper, PlexCollectionHelper
import pmm_cfg_gen.utils.template_filters as template_filters

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
            self._logger.debug("Unable to load requested template: '{}'".format(templateName))

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
            except jinja2.exceptions.TemplateNotFound:
                self._logger.debug("Requested Template does not exist: '{}'".format(templateName))

                return None
            except (
                jinja2.TemplateSyntaxError,
                jinja2.exceptions.UndefinedError,
            ) as exTpl:
                self._logger.error(
                    "Failed to load template: '{}'. Exception: {}".format(
                        templateName, str(exTpl)
                    )
                )
                if self._logger.isEnabledFor(logging.DEBUG):
                    self._logger.exception(
                        "Template Syntax Error: '{}'".format(templateName)
                    )

                return None
            except:
                if self._logger.isEnabledFor(logging.DEBUG):
                    self._logger.exception(
                        "Failed to load template: '{}'".format(templateName)
                    )

                return None

        else:
            self._logger.debug(
                "Retrieving template from cache: {}".format(templateName)
            )

        return self.__cachedTemplates[templateName]

    def __registerFilters(self):
        self.__tplEnv.filters["formatJson"] = template_filters.formatJson
        self.__tplEnv.filters["concat"] = template_filters.concat
        self.__tplEnv.filters["quote"] = template_filters.quote
        self.__tplEnv.filters["add_prepostfix"] = template_filters.add_prepostfix
        
        self.__tplEnv.filters["formatItemTitle"] = PlexItemHelper.formatItemTitle
        self.__tplEnv.filters["isPMMItem"] = PlexItemHelper.isPMMItem
        self.__tplEnv.filters["getPMMSeason"] = template_filters.getPMMSeason
        
        self.__tplEnv.filters["generateTpDbSearchUrl"] = template_filters.generateTpDbSearchUrl
        self.__tplEnv.filters["getItemGuidByName"] = template_filters.getItemGuidByName
        self.__tplEnv.filters["getNamedCollectionLabels"] = template_filters.getNamedCollectionLabels
        self.__tplEnv.filters["getCollectionGuidsByName"] = template_filters.getCollectionGuidsByName
        self.__tplEnv.filters["getTmDbCollectionId"] = template_filters.getTmDbCollectionId
        self.__tplEnv.filters["getPMMAttributeByName"] = template_filters.getPMMAttributeByName
        # self.__tplEnv.filters["getTvDbListId"] = template_filters.getTvDbListId
