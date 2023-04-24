#!/usr/bin/env python3
###################################################################################################

# import trakt
import logging
import jsonpickle

from pmm_cfg_gen.utils.settings_utils_v1 import globalSettingsMgr

###################################################################################################


# https://pytrakt.readthedocs.io/en/latest/getstarted.html
# https://github.com/moogar0880/PyTrakt
class TraktHelper:
    __logger: logging.Logger

    def __init__(self) -> None:
        self.__logger = logging.getLogger("pmm-cfg-gen")

        # self.__loggerFunc = self.__logger.debug
        self.__loggerFunc = print

        if (
            globalSettingsMgr.settings.theTvDatabase.apiKey is not None
            and len(globalSettingsMgr.settings.theTvDatabase.apiKey) > 0
            and globalSettingsMgr.settings.theTvDatabase.pin is not None
        ):
            self.__loggerFunc("Initalizing trakt connection")
        else:
            self.__tvdbApi = None

    def getListByName(self, name: str) -> str | None:
        self.__loggerFunc("Searching for trakt list: {}".format(name))

        # result = self.__tvdbApi.get_all_lists(meta= { "menu[type]" : "list", "query": name } )

        # self.__loggerFunc("trakt result: {}".format(jsonpickle.dumps(result, unpicklable=False)))

        return ""
