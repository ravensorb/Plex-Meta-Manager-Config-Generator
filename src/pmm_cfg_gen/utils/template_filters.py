#!/usr/bin/env python3
#######################################################################

import json
import logging
import jsonpickle
import urllib.parse
import requests
import typing as t
import re
from jinja2.exceptions import FilterArgumentError

from dotty_dict import dotty

from plexapi.library import LibrarySection
from plexapi.collection import Collection
from plexapi.video import Video, Movie, Show

from pmm_cfg_gen.utils.settings_utils_v1 import globalSettingsMgr
from pmm_cfg_gen.utils.plex_utils import PlexItemHelper, PlexVideoHelper, PlexCollectionHelper
from pmm_cfg_gen.utils.tmdb_utils import TheMovieDatabaseHelper
# from pmm_cfg_gen.utils.tvdb_utils import TheTvDatabaseHelper

#######################################################################
# Jinja2 filters and utilitiy methods


def concat(*args: t.Any, **kwargs: t.Any) -> list:
    """
     Concatenates arguments to a list. This is useful for filters that need to combine iterables and lists into a single list
     
     @param args - The arguments to be concatenated
     @param kwargs - The keyword arguments to be concatenated
     
     @return A new list with all the arguments concatenated into it.
    """
    result = []

    # Add prefix postfix and prefix arguments to the arguments.
    if not args:    
        # Raise an exception if keyword arguments are not keyword arguments.
        if kwargs:
            raise FilterArgumentError(
                f"Unexpected keyword argument {next(iter(kwargs))!r}"
            )
    else:
        try:
            for a in args:
                if isinstance(a, (list, tuple)):
                    result.extend(a)
                else:
                    result.append(str(a))

        except LookupError:
            raise FilterArgumentError("concat requires a prefix and postfix argument") from None

    result = list(set(list(map(str, result))))

    while ("" in result):
        result.remove("")

    return result

def formatJson(data, indent: int = 4):
    """
     Formats data to JSON. This is a helper function for L { jsonpickle. dumps } that does not include unpicklable objects.
     
     @param data - The data to format. It must be a dictionary or an iterable
     @param indent - The number of spaces to indent the JSON.
     
     @return A JSON representation of the data as a string. The output is guaranteed to be UTF - 8 encoded
    """
    return json.dumps(json.loads(str(jsonpickle.dumps(data, indent=indent, unpicklable=False))), indent=indent)

def quote(data : str, quateChar : str = "\"") -> str:
    """
     Quote string
     
     @param data - The data to quote.
     @param quateChar - The character to use for quoting.
     
     @return The quoted data if it contains spaces otherwise the original data is returned as is. 
    """
    # Returns a string with the quate character.
    if " " in data.strip():
        return "{}{}{}".format(quateChar, data, quateChar)

    return data

def add_prepostfix(data : str, *args: t.Any, **kwargs: t.Any):
    """
     Add prefix and postfix to data if not already present. This is useful for filters that don't want to prefix or postfix the data to be sent to the filter
     
     @param data - The data to check for prefix and postfix
     @param args - The arguments to be checked for prefix and postfix
     @param kwargs - The keyword arguments to be checked for prefix and postfix
     
     @return The data with prefix and postfix added to it if not already present or stripped of any pre - or
    """
    prefix = None
    postfix = None 

    # Add prefix postfix and prefix arguments to the arguments.
    if not args:    
        # If prefix is not specified the prefix is used.
        if "prefix" in kwargs:
            prefix = kwargs.pop("prefix", None)

        # If postfix is not present in kwargs it will be removed from the postfix dictionary.
        if "postfix" in kwargs:
            postfix = kwargs.pop("postfix", None)

        # Raise an exception if keyword arguments are not keyword arguments.
        if kwargs:
            raise FilterArgumentError(
                f"Unexpected keyword argument {next(iter(kwargs))!r}"
            )
    else:
        try:
            prefix = args[0]
            postfix = args[1:]
        except LookupError:
            raise FilterArgumentError("add_prepostfix requires a prefix and postfix argument") from None

    # Append prefix to data if prefix is not empty
    if prefix and not data.strip().startswith(prefix):
        data = "{}{}".format(prefix, data)

    # Returns a string with the postfix appended to the data.
    if postfix and not data.strip().endswith(postfix):
        data = "{}{}".format(data, postfix)

    #print("add_prepostfix: {}".format(data))
    
    return data
        
def generateTpDbSearchUrl(item, baseUrl=None) -> str:
    """
     Generates URL forthePosterDatabase search. 
     
     @param item - The item to search for. It must have a title and subtype
     @param baseUrl - The base URL to use. If None the value from the PosterDatabase
     
     @return The URL that should be used to search for the item in Taxonomy Poster Database. If it's None the URL will be based on the settings
    """
    # Set the base URL to search URL if not set.
    if baseUrl is None:
        baseUrl = (
            globalSettingsMgr.settings.thePosterDatabase.searchUrlPro
            if globalSettingsMgr.settings.thePosterDatabase.enablePro
            else globalSettingsMgr.settings.thePosterDatabase.searchUrl
        )

    urlParms = {}

    urlParms.update({"term": item.title})

    if globalSettingsMgr.settings.thePosterDatabase.enablePro:
        if item.type == "collection":
            urlParms.update({"category": "Collections"})
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

    # logging.getLogger("pmm-cfg-gen").info(urlParms)

    urlQS = urllib.parse.urlencode(urlParms, quote_via=urllib.parse.quote)

    req = requests.PreparedRequest()
    req.prepare_url(baseUrl, urlQS)

    return str(req.url)

def getItemGuidByName(item, guidName: str) -> str | None:
    """
     Get the Guid associated with an item. This is a wrapper around L { PlexItemHelper. getGuidByName }
     
     @param item - The item to get the guid from
     @param guidName - The name of the guid
     
     @return The Guid or None if not
    """
    s = ""

    if isinstance(item, Video):
        plexItem = PlexVideoHelper(item)

        s = plexItem.getGuidByName(guidName)
    elif isinstance(item, Collection):
        plexCollection = PlexCollectionHelper(item)

        guids = plexCollection.getGuidByName(guidName)
        if guids: 
            s = ", ".join(guids)
    else: 
        s = ""

    #logging.getLogger("pmm-cfg-gen").debug("{}: Guid '{}' is '{}'".format(type(item), guidName, s))
    
    return s

def getNamedCollectionLabels(item) -> list[str] | None:
    return PlexItemHelper.getNamedCollectionLabels(item)

def getCollectionGuidsByName(collection, guidName: str) -> list | None:
    """
     Get a list of Guid's from a PlexCollection. This is a convenience function to call L { PlexCollectionHelper }'s C { getGuidByName } method
     
     @param collection - A collection object or path to a collection
     @param guidName - The name of the Guid
     
     @return A list of G
    """
    pch = PlexCollectionHelper(collection)

    return pch.getGuidByName(guidName)

def getTmDbCollectionId(collection, tryExactMatch : bool = True) -> list[int] | None:
    """
     Get Tmdb collection ID. This is a wrapper around the TMDb findCollectionByName function to allow searching for collections by title
     
     @param collection - Collection to be looked up
     @param tryExactMatch - If True try to find exact match
     
     @return Collection ID or None if not found or no collection could be found in the TMDb ( not an exception
    """
    
    tmdbHelper = TheMovieDatabaseHelper()

    return tmdbHelper.findCollectionByName(collection.title, tryExactMatch)

def getPMMSeason(pmm : dict[str, dict], seasonNumber, attribute : str | None = None):
    """
     Get the poster URL for a season from the Plex Meta Manager season dictionary
     
     @param pmm - The Plex Meta Manager season dictionary
     @param seasonNumber - The season number
     
     @return The season or None if not found
    """
    if pmm is None: return None

    if "seasons" in pmm.keys():
        for season in pmm["seasons"]:
            if season == seasonNumber:
                return pmm["seasons"][season][attribute] if attribute in pmm["seasons"][season] else pmm["seasons"][season]

    return None

def getPMMAttributeByName(pmm : dict[str, dict], attribute : str | None = None):
    if pmm is None: return None

    tmp = dotty(pmm)

    if tmp.get(attribute) is not None: return tmp.get(attribute)
    if tmp.get("variables.{}".format(attribute)) is not None: return tmp.get("variables.{}".format(attribute))
    if tmp.get("template.{}".format(attribute)) is not None: return tmp.get("template.{}".format(attribute))

    return None

# def getTvDbListId(collection) -> list[int] | str | None:
#     tvDbHelper = TheTvDatabaseHelper()

#     return tvDbHelper.findListByName(collection.title)
