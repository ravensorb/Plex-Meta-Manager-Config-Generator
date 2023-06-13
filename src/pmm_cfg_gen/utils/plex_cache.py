#!/usr/bin/env python3
###################################################################################################

import jsonpickle
import json_fix

from plexapi.library import Library
from plexapi.collection import Collection
from plexapi.media import Media
from pmm_cfg_gen.utils.plex_utils import PlexItemHelper

###################################################################################################
class PlexLibraryCache:
    library: str
    collections: list[dict]
    items: list[dict]

    def __init__(self, libraryName: str) -> None:
        __libraryName = libraryName

        self.collections = list()
        self.items = list()

    def addCollection(self, collection: Collection):
        if not self.__isCollectionCached(collection):
            self.collections.append({"title": collection.title, "metadata": collection})

    def addMediaItem(self, item: Media):
        if not self.__isItemCached(item):
            itemTitle = PlexItemHelper.formatItemTitle(item) # type: ignore
            self.items.append({"title": itemTitle, "metadata": item})

    def to_cached_items_dict(self) -> dict:
        return {"collections": self.collections, "items": self.items}

    def to_stats_dict(self) -> dict:
        return {"collections": len(self.collections), "items": len(self.items)}

    def __json__(self):
        return self.toDict()

    def toDict(self) -> dict:
        return {
            "library": self.library,
            "items": self.to_cached_items_dict(),
            "stats": self.to_stats_dict(),
        }

    def __isCollectionCached(self, item) -> bool:
        it = next(
            (x for x in self.collections if x["title"] == item.title),
            None,
        )

        return it is not None

    def __isItemCached(self, item) -> bool:
        it = self.findByItem(item)

        return it is not None

    def findByItem(self, item):
        it = next(
            (
                x
                for x in self.items
                if x["title"] == PlexItemHelper.formatItemTitle(item) or 
                    ("orig_title" in x and x["orig_title"] == PlexItemHelper.formatItemTitle(item)) or 
                    ("alt_title" in x and x["alt_title"] == PlexItemHelper.formatItemTitle(item))
            ),
            None,
        )

        return it

class PlexCache:
    __cache: dict[str, PlexLibraryCache]

    def __init__(self) -> None:
        self.__cache = dict()

    def addLibraryEntry(self, library: Library) -> PlexLibraryCache:
        self.__cache[library.title1] = PlexLibraryCache(library.title1)

        return self.__cache[library.title1]

    def getLibraryCache(self, library):
        self.__cache[library.title1]

    def __json__(self):
        return self.toDict()

    def toDict(self):
        result = {
            "items": self.__cache,
            "stats": {"libraries": len(self.__cache.keys())},
        }

        return result
