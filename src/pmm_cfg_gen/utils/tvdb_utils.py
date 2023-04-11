# #!/usr/bin/env python3
# ###################################################################################################

# import tvdb_v4_official
# import logging
# import jsonpickle
# from pmm_cfg_gen.utils.settings_yml import globalSettingsMgr

# ###################################################################################################

# class TheTvDatabaseHelper:
#     __logger: logging.Logger
#     __tvdbApi : tvdb_v4_official.TVDB | None

#     def __init__(self) -> None:
#         self.__logger = logging.getLogger("pmm-cfg-gen")

#         #self.__loggerFunc = self.__logger.debug
#         self.__loggerFunc = print

#         if globalSettingsMgr.settings.theTvDatabase.apiKey is not None and len(globalSettingsMgr.settings.theTvDatabase.apiKey) > 0 and globalSettingsMgr.settings.theTvDatabase.pin is not None:
#             self.__loggerFunc("Initalizing tvdb connection")
#             self.__tvdbApi = tvdb_v4_official.TVDB(globalSettingsMgr.settings.theTvDatabase.apiKey, pin=globalSettingsMgr.settings.theTvDatabase.pin)
#         else:
#             self.__tvdbApi = None

#     def findListByName(self, name : str) -> list[int] | str:
#         if self.__tvdbApi is None: return ""

#         self.__loggerFunc("Searching for tvdb list: {}".format(name))

#         result = self.__tvdbApi.get_all_lists(meta= { "menu[type]" : "list", "query": name } )

#         self.__loggerFunc("tvdb result: {}".format(jsonpickle.dumps(result, unpicklable=False)))

#         return ""
