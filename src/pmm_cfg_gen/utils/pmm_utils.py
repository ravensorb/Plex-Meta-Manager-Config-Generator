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
                self._logger.error("Error parsing YAML file '{}'. Details: {}".format(fileName, exc))
            except Exception as exc:
                self._logger.error("Invalid PMM file '{}'. Details: {}".format(fileName, exc))

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
            "label": self.__getAttributeListFromItemByName(data, "label"),
            "collection": self.__getAttributeListFromItemByName(data, "collection"),
            "list": self.__getAttributeListFromItemByName(data, "list"),
            "movie": self.__getAttributeListFromItemByName(data, "movie"),
            "show": self.__getAttributeListFromItemByName(data, "show"),
            "poster": self.__getPosterUrlFromItem(data),
            "trakt": self.__getAttributeListFromItemByName(data, "trakt_list"),
            "sort": {
                "prefix": self.__getAttributeFromItemByName(data, "sort_prefix"),
                "order": self.__getAttributeFromItemByName(data, "sort_order"),
                "separator": self.__getAttributeFromItemByName(data, "sort_separator"),
            }
        }

        return result

    def metadataItem_to_dict(self, metadataName: str, year : int | None = None) -> dict[str, Any] | None:
        data = self.getMetadataCacheByName(metadataName, year)

        if data is None: return None
        
        result = {
            "title": data["title"] if "title" in data else metadataName,

            "poster": self.__getPosterUrlFromItem(data),

            "label": self.__getAttributeListFromItemByName(data, "label"),

            "movie": self.__getAttributeListFromItemByName(data, "movie"),
            "show": self.__getAttributeListFromItemByName(data, "movie"),
            "list": self.__getAttributeListFromItemByName(data, "list"),
            "collection": self.__getAttributeListFromItemByName(data, "collection"),

            "sort_prefix": self.__getAttributeFromItemByName(data, "sort_prefix"),
            "sort_order": self.__getAttributeFromItemByName(data, "sort_order"),
            "sort_separator": self.__getAttributeFromItemByName(data, "sort_separator"),
        }

        if "seasons" in data:
            result.update( {"seasons": self.getPosterUrlsFromMetadataSeasons(metadataName, year) } )

        return result
    
    ###################################################################################################
    def getCollectionCacheByName(self, name : str) -> dict | None:
        self._logger.debug("Getting collection cache by name: '{}'".format(name))
        
        result = self.__collectionCache[name] if name in self.__collectionCache else None
        if result is None:
            result = next((x for x in self.__collectionCache if ("title" in x and x["title"] == name) or ("alt_title" in x and x["alt_title"] == name) or ("orig_title" in x and x["orig_title"] == name)), None)

        return result
    
    def getMetadataCacheByName(self, name : str, year : int | None) -> dict | None:
        self._logger.debug("Getting metadata cache by name: '{}'".format(name))
        
        result = self.__metadataCache[name] if name in self.__metadataCache else None

        if result is None:
            name = name.strip()
            self._logger.debug("Metadata cache by name: '{}' not found, searching by title".format(name))
            for k in self.__metadataCache:
                v = self.__metadataCache[k]
                #self._logger.info("Metadata cache by name: '{}' checking title: '{}'".format(name, x))
                if ("title" in v and v["title"].strip() == name) or ("alt_title" in v and v["alt_title"].strip() == name) or ("orig_title" in v and v["orig_title"].strip() == name): 
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
        if "seasons" in data and data["seasons"] is not None and len(data["seasons"]) > 0:
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

        result = self.__getAttributeListFromItemByName(data, listName)
            
        return result

    def __getAttributeListFromItemByName(self, data : dict, attribute : str) -> list | None:
        result = self.__stringCollectionToList(self.__getAttributeFromItemByName(data, attribute))

        return result

    def __getAttributeFromItemByName(self, data : dict, attribute : str) -> str | None:
        if data is None: return None
        
        self._logger.debug("Getting '{}' from item".format(attribute))

        result : str | None = None

        if attribute in data: 
            self._logger.debug("Searching Root: '{}'".format(data[attribute]))
            return data[attribute]

        if "template" in data:
            self._logger.debug("Searching Template: '{}'".format(data["template"]))

            if isinstance(data["template"], list) and len(data["template"]) > 0:
                result = ""
                for x in data["template"]:
                    if attribute in x: result += ", ".join(x[attribute])

                if result and len(result) > 0: return result.strip()
            elif isinstance(data["template"], dict) and attribute in data["template"]: 
                self._logger.debug("Found: '{}' in '{}'".format(attribute, data["template"][attribute]))
                return data["template"][attribute]
            else:
                self._logger.error("Invalid template: '{}'".format(data["template"]))

        if "variables" in data:
            self._logger.debug("Searching Variable: '{}'".format(data["variables"]))
            if attribute in data["variables"]: 
                self._logger.debug("Found: '{}' in '{}'".format(attribute, data["variables"][attribute]))
                return data["variables"][attribute]
            
        return result

    def __getPosterUrlFromItem(self, data : dict) -> str | None:
        if data is None: return None
        
        self._logger.debug("Getting Poster Url from: '{}'".format(data))
        
        posterUrl = self.__getAttributeListFromItemByName(data, "poster")
        if posterUrl is None or len(posterUrl) == 0 or posterUrl == "": posterUrl = self.__getAttributeListFromItemByName(data, "url_poster")

        self._logger.debug("Poster Url: '{}'".format(posterUrl))
        
        if posterUrl is None or len(posterUrl) == 0: 
            return None

        return str(posterUrl[0]) if isinstance(posterUrl, list) else str(posterUrl)

    def __stringCollectionToList(self, collection : str | list | None) -> list[str]:
        if collection is None: return []        

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