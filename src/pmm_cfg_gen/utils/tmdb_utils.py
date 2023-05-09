#!/usr/bin/env python3
###################################################################################################

import themoviedb
import logging
import jsonpickle

from pmm_cfg_gen.utils.settings_utils_v1 import globalSettingsMgr

###################################################################################################


class TheMovieDatabaseHelper:
    __logger: logging.Logger
    __tmdbApi: themoviedb.TMDb | None

    def __init__(self) -> None:
        self.__logger = logging.getLogger("pmm-cfg-gen")

        self.__loggerFunc = self.__logger.debug
        # self.__loggerFunc = print

        if (
            globalSettingsMgr.settings.theMovieDatabase.apiKey is not None
            and len(globalSettingsMgr.settings.theMovieDatabase.apiKey) > 0
        ):
            self.__loggerFunc("Initalizing tmdb connection")
            self.__tmdbApi = themoviedb.TMDb(
                key=globalSettingsMgr.settings.theMovieDatabase.apiKey,
                language=globalSettingsMgr.settings.theMovieDatabase.language,
                region=globalSettingsMgr.settings.theMovieDatabase.region,
            )
        else:
            self.__tmdbApi = None

    def findCollectionByName(self, name: str, exactMatch: bool = False) -> list[int]:
        if self.__tmdbApi is None:
            return []

        name = name.strip()
        
        self.__loggerFunc("Searching for collection: '{}'".format(name))

        searchResults = self.__tmdbApi.search().collections(
            name
        ) 

        self.__loggerFunc(
            "tmdb result: {}".format(jsonpickle.dumps(searchResults, unpicklable=False))
        )

        results = []
        
        if searchResults is not None and searchResults.results is not None:
            if exactMatch:
                results = [x.id for x in searchResults.results if x.name == name or x.name == f"{name} Collection" ]

            if not exactMatch or len(results) == 0:
                results = [x.id for x in searchResults.results]

        if (
            globalSettingsMgr.settings.theMovieDatabase.limitCollectionResults is not None
            and globalSettingsMgr.settings.theMovieDatabase.limitCollectionResults > 0
            and results is not None and len(results) > 0
            and len(results) > globalSettingsMgr.settings.theMovieDatabase.limitCollectionResults
        ):
            results = results[
                : globalSettingsMgr.settings.theMovieDatabase.limitCollectionResults
            ]
        
        return results if results is not None else []
