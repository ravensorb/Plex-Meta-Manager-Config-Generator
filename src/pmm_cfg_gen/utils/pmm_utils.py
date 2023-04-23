#!/usr/bin/env python3
###################################################################################################

import logging
import os
from pathlib import Path
from typing import Any
import ruamel.yaml

###################################################################################################
class PlexMetaManagerCache:
    _logger: logging.Logger

    __collectionCache: dict
    __metadataCache: dict
    __overlayCache: dict

    def __init__(self) -> None:
        self._logger = logging.getLogger("pmm_cfg_gen")

        self.__collectionCache = {}
        self.__metadataCache = {}
        self.__overlayCache = {}

    def processFolder(self, path):
        self._logger.info("Processing Folder: '{}'".format(path))

        for root, dirs, files in os.walk(path):
                for file in files:
                    self.loadFile(Path(root, file)) 

        self._logger.info("Collections Processed: {}".format(len(self.__collectionCache)))
        self._logger.info("Metadata Processed: {}".format(len(self.__metadataCache)))
        self._logger.info("Overlays Processed: {}".format(len(self.__overlayCache)))
        
    def loadFile(self, fileName):
        self._logger.debug("Loading File: '{}'".format(fileName))

        with open(fileName, "r") as fp:
            try:
                data = ruamel.yaml.load(fp, Loader=ruamel.yaml.Loader)
                if data is None: return

                if "collections" in data:
                    for it in data["collections"]:
                        if it is not None:
                            self.__collectionCache[it] = data["collections"][it]

                if "metadata" in data:
                    for it in data["metadata"]:
                        if it is not None:
                            self.__metadataCache[it] = data["metadata"][it]

                if "overlays" in data:
                    for it in data["overlays"]:
                        if it is not None:
                            self.__overlayCache[it] = data["overlays"][it]

            except ruamel.yaml.YAMLError as exc:
                self._logger.error("Error parsing YAML file: {}".format(exc))

    def saveResultsToYaml(self, fileName : str | Path):
        self._logger.info("Saving results to file: '{}'".format(fileName))

        with open(fileName, "w") as fp:
            ruamel.yaml.round_trip_dump({"collections": self.__collectionCache, "metadata": self.__metadataCache}, fp)

    def collectionItem_to_dict(self, collectionName: str) -> dict[str, Any] | None:
        data = self.getCollectionCacheByName(collectionName)

        if data is None: return None

        self._logger.debug("collectionItem_to_dict: {}".format(data))
        
        result = {
            "title": data["title"] if "title" in data else collectionName,
            "collection": self.__getAttributeFromItemByName(data, "collection"),
            "list": self.__getAttributeFromItemByName(data, "list"),
            "movie": self.__getAttributeFromItemByName(data, "movie"),
            "show": self.__getAttributeFromItemByName(data, "show"),
            "poster": self.__getPosterUrlFromItem(data),
            "trakt": self.__getAttributeFromItemByName(data, "trakt_list"),
        }

        return result

    def metadataItem_to_dict(self, metadataName: str, year : int | None = None) -> dict[str, Any] | None:
        data = self.getMetadataCacheByName(metadataName, year)

        if data is None: return None
        
        result = {
            "title": data["title"] if "title" in data else metadataName,
            "poster": self.__getPosterUrlFromItem(data),            
        }

        if "seasons" in data:
            result.update( {"seasons": self.getPosterUrlsFromMetadataSeasons(metadataName, year) } )

        return result
    
    ###################################################################################################
    def getCollectionCacheByName(self, name : str) -> dict | None:
        self._logger.debug("Getting collection cache by name: '{}'".format(name))
        
        result = self.__collectionCache[name] if name in self.__collectionCache else None
        if result is None:
            result = next((x for x in self.__collectionCache if "title" in x and x["title"] == name), None)

        return result
    
    def getMetadataCacheByName(self, name : str, year : int | None) -> dict | None:
        self._logger.debug("Getting metadata cache by name: '{}'".format(name))
        
        result = self.__metadataCache[name] if name in self.__metadataCache else None

        if result is None:
            self._logger.debug("Metadata cache by name: '{}' not found, searching by title".format(name))
            for k in self.__metadataCache:
                v = self.__metadataCache[k]
                #self._logger.info("Metadata cache by name: '{}' checking title: '{}'".format(name, x))
                if "title" in v and v["title"].strip() == name.strip(): 
                    if year is None:
                        result = v 
                        break
                    elif year-1 <= v["year"] <= year+1:
                        self._logger.debug("Metadata cache by name: '{}' found by title".format(name))
                        result = v

                        break
            
        return result

    def getOverlayCacheByName(self, name : str) -> dict | None:
        self._logger.debug("Getting overlay cache by name: '{}'".format(name))
        
        result = self.__overlayCache[name] if name in self.__overlayCache else None
        
        if result is None:
            result = next((x for x in self.__overlayCache if "title" in x and x["title"] == name), None)

        return result

    def getPosterUrlFromCollection(self, collectionName : str) -> str | None:
        data = self.getCollectionCacheByName(collectionName)
        if data is None:
            return None

        self._logger.debug("Getting Poster Url from collection: '{}'".format(collectionName))
        
        return self.__getPosterUrlFromItem(data)

    def getPosterUrlFromMetadata(self, metadataName : str, year : int | None) -> str | None:
        data = self.getMetadataCacheByName(metadataName, year)
        if data is None:
            return None

        self._logger.debug("Getting Poster Url from metadata: '{}'".format(metadataName))

        return self.__getPosterUrlFromItem(data)

    def getPosterUrlsFromMetadataSeasons(self, metadataName : str, year : int | None) -> dict[str, dict] | None:
        data = self.getMetadataCacheByName(metadataName, year)
        if data is None:
            return None

        self._logger.debug("Getting Poster Urls from metadata: '{}'".format(metadataName))

        result = {}
        if "seasons" in data:
            for k in data["seasons"]:
                result[k] = { "poster": self.__getPosterUrlFromItem(data["seasons"][k]) }

        return result
    
    def getPosterUrlFromMetadataSeason(self, metadataName : str, season: int, year : int | None = None) -> str | None:
        result = self.getPosterUrlsFromMetadataSeasons(metadataName, year)

        if result is not None and str(year) in result.keys():
            return result[str(year)]["poster"] if "poster" in result[str(year)] else None
        
        return None

    def getShowListFromCollection(self, collectionName : str) -> list | None:
        data = self.getCollectionCacheByName(collectionName)
        if data is None:
            return None

        result = self.__getItemIDsFromCollectionByName(collectionName, "show")

        return result if type(result) is list else [result]

    def getMovieListFromCollection(self, collectionName : str) -> list | None:
        data = self.getCollectionCacheByName(collectionName)
        if data is None:
            return None

        result = self.__getItemIDsFromCollectionByName(collectionName, "movie")

        return result if type(result) is list else [result]

    def getCollectionListFromCollection(self, collectionName : str) -> list | None:
        data = self.getCollectionCacheByName(collectionName)
        if data is None:
            return None

        result = self.__getItemIDsFromCollectionByName(collectionName, "collection")

        return result if type(result) is list else [result]

    def getListsFromCollection(self, collectionName : str) -> list | None:
        data = self.getCollectionCacheByName(collectionName)
        if data is None:
            return None

        result = self.__getItemIDsFromCollectionByName(collectionName, "list")

        return result if type(result) is list else [result]

    ###################################################################################################
    def __getItemIDsFromCollectionByName(self, collectionName : str, listName : str) -> list | None:
        data = self.getCollectionCacheByName(collectionName)
        if data is None:
            return None
        
        self._logger.debug("Getting '{}' from collection: '{}'".format(listName, collectionName))
        self._logger.debug("Data: '{}'".format(data))

        result = self.__getAttributeFromItemByName(data, listName)
            
        return result

    def __getAttributeFromItemByName(self, data : dict, attribute : str) -> list | None:
        self._logger.debug("Getting '{}' from item: '{}'".format(attribute, data))

        result = []

        if attribute in data: 
            self._logger.debug("Searching Root: '{}'".format(data[attribute]))
            return self.__stringCollectionToList(data[attribute])

        if "template" in data:
            self._logger.debug("Searching Template: '{}'".format(data["template"]))
            if attribute in data["template"]: return self.__stringCollectionToList(data["template"][attribute])

        if "variables" in data:
            self._logger.debug("Searching Variable: '{}'".format(data["variables"]))
            if attribute in data["variables"]: return self.__stringCollectionToList(data["variables"][attribute])
            
        return result

    def __getPosterUrlFromItem(self, data : dict) -> str | None:
        self._logger.debug("Getting Poster Url from: '{}'".format(data))
        
        posterUrl = self.__getAttributeFromItemByName(data, "url_poster")
        if posterUrl is None or len(posterUrl) == 0: posterUrl = self.__getAttributeFromItemByName(data, "poster")

        self._logger.debug("Poster Url: '{}'".format(posterUrl))
        
        if posterUrl is None or len(posterUrl) == 0: 
            return None

        return str(posterUrl[0]) if isinstance(posterUrl, list) else str(posterUrl)

    def __stringCollectionToList(self, collection : str | list) -> list[str]:

        if isinstance(collection, list):
            return list(map(str, collection))
        
        return [x.strip() for x in collection.split(",")] if isinstance(collection, str) else [collection]
    
    ###################################################################################################
    ###################################################################################################
    ###################################################################################################
    ###################################################################################################
    
def test_PlexMetaManager(path: str, showName : str = "Bosch", year : int | None = None):
    pmm = PlexMetaManagerCache()

    p = Path(path)

    if p.exists():
        pmm.processFolder(p)

        pmm.saveResultsToYaml(Path(p.parent, Path(p.stem, "pmm_summary.yaml")))

        print("{} Poster: {}".format(showName, pmm.getPosterUrlFromCollection(showName)))
        print("{} Show List: {}".format(showName, pmm.getShowListFromCollection(showName)))
        print("{} Season 1 Poster: {}".format(showName, pmm.getPosterUrlFromMetadataSeason(showName, 1, 2015)))
    else:
        print("Path does not exist: {}".format(p))

if __name__ == "__main__":

    import sys
    logging.basicConfig(level=logging.INFO)
    test_PlexMetaManager(sys.argv[1], "Bosch", 2012) 