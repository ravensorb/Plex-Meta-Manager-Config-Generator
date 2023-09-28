#!/usr/bin/env python3
###################################################################################################

import logging

import jsonpickle.handlers
import json
from plexapi.base import PlexObject, PlexPartialObject
from plexapi.library import LibrarySection
from plexapi.collection import Collection
from plexapi.video import Video, Movie, Show
from plexapi.audio import Artist
from plexapi.server import PlexServer
import plexapi.utils
import re

from pmm_cfg_gen.utils.settings_utils_v1 import SettingsPlexLibrary, globalSettingsMgr

###################################################################################################

# @jsonpickle.handlers.register(PlexObject, base=True)
class PlexJsonHandler(jsonpickle.handlers.BaseHandler):
    def flatten(self, obj, data):
        """
         Flatten a Plex object into a dictionary. This is useful for generating JSON - RPC responses from server - side
         
         @param obj - The object to be flattened
         @param data - The dictionary to be flattened into. Should be an empty dictionary
         
         @return The dictionary with flattened objects as key / value pairs in the form of a dictionary ( field_name : value )
        """
        # Fix url raise
        # Set the _baseurl attribute of obj to the PlexServer.
        if isinstance(obj, PlexServer):
            setattr(obj, "_baseurl", globalSettingsMgr.settings.plex.serverUrl)

        if hasattr(obj, "toJson") and callable(getattr(obj, "toJson")) and False:
            data = json.loads(plexapi.utils.toJson(obj)) # This doesn't get all of the childern objects correctly
        else:
        # remove methods, private fields etc
            members = []

            for attr in dir(obj):
                try:
                    if not callable(getattr(obj, attr)) and not attr.startswith("__") and not attr.startswith("_"):
                        members.append(attr)
                except AttributeError:
                    pass
                
            # flatten all members of the class and add them to data
            for normal_field in members:
                # we use context flatten - so its called handlers for given class
                data[normal_field] = self.context.flatten(getattr(obj, normal_field), {})

        return data

    def restore(self, obj):
        """
         Restore a previously saved object. This is called by : meth : ` save ` when the object is saved to the database.
         
         @param obj - The object to restore. This can be anything that can be converted to a database object by : meth : ` save `.
         
         @return The restored object. Note that this will be a copy of the object passed in but it is up to the caller to make sure that the object is not modified
        """
        return super().restore(obj)


jsonpickle.handlers.registry.register(PlexObject, PlexJsonHandler, True)

###################################################################################################

class PlexItemHelper:
    @classmethod
    def isPMMItem(cls, item: PlexPartialObject):
        """
         Checks if item is PMM item. This is used to detect items that are part of an emmy awards
         
         @param cls - class that contains the item
         @param item - item that is to be checked for PMM
         
         @return True if item is part of emmy awards False if it is not part of emmy a
        """
        # Check if the item is a PMM item.
        for label in item.labels:
            # Check if label is a PMM item
            if str(label.tag).strip() in [
                "Decade",
                "Emmy Awards",
                "Golden Globes Awards",
                "Top Actors",
                "Top Directors",
                "Oscars Winners Awards",
            ]:
                logging.getLogger("pmm_cfg_gen").debug(
                    "isPMMItem Found: {} - {}".format(item.title, label.tag)
                )
                return True

            # Check if item is a PMM item
            if str(item.title).strip() in [
                "Golden Globes Best Director Winners",
                "Golden Globes Best Picture Winners",
                "Oscars Best Director Winners",
                "Oscars Best Picture Winners",
                "Newly Released",
                "New Episodes",
                "TMDb Airing Today",
                "TMDb On The Air",
            ]:
                logging.getLogger("pmm_cfg_gen").debug(
                    "isPMMItem Found: {} - {}".format(item.title, label.tag)
                )
                return True

        return False
    
    @classmethod
    def cleanString(cls, title: str) -> str:
        """
         Cleans a title to make it suitable for display. This is a helper function for L { Title } and L { TitleFromText }.
         
         @param cls - The class that defines the type of title to be cleaned.
         @param s - The title to be cleaned. This should be a string that has no punctuation or other non - alphanumeric characters.
         
         @return A string that has all characters in the form of a - zA - Z0 - 9 and underscores
        """
        return title.replace("/", "-").replace("\\", "-").replace(":", "-").replace("*", "-").replace("?", "-").replace("\"", "-").replace("<", "-").replace(">", "-").replace("|", "-")

    @classmethod
    def formatString(cls, formatString: str, library : LibrarySection | None = None, collection : Collection | None = None, item : Video | Artist | None = None, pmm : dict | None = None, librarySettings : SettingsPlexLibrary | None = None, cleanTitleStrings : bool = False) -> str:
        """
        The format string to format. This is a string with placeholders to be substituted.
        
        @param cls - The class that owns the LibrarySection. Defaults to None.
        @param library - The LibrarySection to format. Defaults to None.
        @param collection - The Collection to format. Defaults to None.
        @param item - The Videobutton to format. Defaults to None.
        
        @return The formatted string if there are placeholders or the original string
        """

        result = formatString

        if librarySettings is not None:
            result = result.replace("{{library.path}}", librarySettings.path) if librarySettings.path else result
        
        if library is not None:
            result = result.replace("{{library.title}}", cls.cleanString(str(library.title)) if cleanTitleStrings else library.title)
            result = result.replace("{{library.type}}", library.type) if library.type else result
            # if no librarySettings.path defined lets use the library.title as a fall back
            result = result.replace("{{library.path}}", cls.cleanString(str(library.title)) if cleanTitleStrings else library.title)

        if collection is not None:
            result = result.replace("{{collection.title}}", cls.cleanString(collection.title) if cleanTitleStrings else collection.title)
            result = result.replace("{{collection.type}}", collection.type if collection.type else "")
            result = result.replace("{{collection.subtype}}", collection.subtype if collection.subtype else "")
            result = result.replace("{{collection.minYear}}", str(collection.minYear) if collection.minYear else "")
            result = result.replace("{{collection.minYear}}", str(collection.maxYear) if collection.maxYear else "")

            if "{{universe}}" in result:
                lstLabels = PlexItemHelper.getNamedCollectionLabels(collection)
                if lstLabels is not None and len(lstLabels) > 0:
                    logging.getLogger("pmm_cfg_gen").debug("formatString collection labels: {}".format(lstLabels))
                    result = result.replace("{{universe}}", lstLabels[0] if lstLabels[0] not in result else "")

        if item is not None:
            result = result.replace("{{item.title}}", cls.cleanString(item.title) if cleanTitleStrings else item.title)
            result = result.replace("{{item.titleSort}}", item.titleSort if item.titleSort else "")

            if isinstance(item, Video):
                result = result.replace("{{item.year}}", str(item.year) if item.year and str(item.year) not in item.title else "")
                result = result.replace("{{item.type}}", item.type if item.type else "")
                result = result.replace("{{item.contentRating}}", item.contentRating if item.contentRating else "")
                result = result.replace("{{item.editionTitle}}", item.editionTitle if isinstance(item, Movie) and item.editionTitle else "")
            elif isinstance(item, Artist):
                pass
    
            if "{{universe}}" in result:
                lstLabels = PlexItemHelper.getNamedCollectionLabels(item)
                if lstLabels is not None and len(lstLabels) > 0:
                    logging.getLogger("pmm_cfg_gen").debug("formatString item labels: {}".format(lstLabels))
                    result = result.replace("{{universe}}", lstLabels[0] if lstLabels[0] not in result else "")

        if pmm is not None:
            if "{{universe}}" in result:
                if "label" in pmm and len(pmm["label"]) > 0:
                    logging.getLogger("pmm_cfg_gen").debug("formatString pmm labels: {}".format(pmm))
                    result = result.replace("{{universe}}", pmm["label"][0] if pmm["label"][0] not in result else "")

        #logging.getLogger("pmm_cfg_gen").debug("formatString Before Cleaning: {} -> {}".format(formatString, result))

        # Lets remove any remaining tokens
        result = re.sub(r"\{\{[^\}]*\}\}", "", result)

        result = result.replace("()", "").replace("[]", "").strip()
        if result.startswith("-"):
            result = result[1:].strip()

        #logging.getLogger("pmm_cfg_gen").debug("formatString After Cleaning: {} -> {}".format(formatString, result))

        return result

    @classmethod
    def cleanItemTitle(cls, item : PlexPartialObject) -> str:
        """
         Clean the title of an item. This is a convenience method for L { cleanTitle }. It removes punctuation and other non - title characters that are illegal in Plex's title and returns the cleaned title.
         
         @param cls - The class to use for this method. Should be a subclass of L { PlexPartialObject }.
         @param item - The item to clean. Should be a L { PlexPartialObject }.
         
         @return The cleaned title of the item as a string. Will be empty if there is no title or it is not valid
        """
        return cls.cleanString(str(item.title))

    @classmethod
    def formatItemTitle(cls, item : Collection | Video | Artist, includeYear : bool = True, includeEdition : bool = True ) -> str:

        strFormat = "{{item.title}}"

        if isinstance(item, Collection):
            return PlexItemHelper.formatString(strFormat, collection=item)
        else:
            if isinstance(item, Video):
                if re.match(r"[\s\S]*\([\d]{4}\)$", item.title, flags=re.DOTALL) is None:
                    strFormat += " ({{item.year}})" if includeYear else ""
                strFormat += " [{{item.editionTitle}}]" if includeEdition and isinstance(item, Movie) else ""
            elif isinstance(item, Artist): 
                pass

            return PlexItemHelper.formatString(strFormat, item=item)

        return ""

    @classmethod
    def getItemLabels(cls, item: PlexPartialObject) -> list[str] | None:
        listResult = []

        listResult = [ x.tag for x in item.labels if x.tag != "PMM" ]

        return listResult

    @classmethod
    def getNamedCollectionLabels(cls, item : PlexPartialObject) -> list[str] | None:
        lstLabels = PlexItemHelper.getItemLabels(item)

        result = []
        if lstLabels is not None:
            result = [ x.replace("PMM-C-", "").replace("PMM-U-", "") for x in lstLabels if x.startswith("PMM-C-") or x.startswith("PMM-U-") ]
            
        return result 
    

class PlexCollectionHelper:
    __collection: Collection
    __guids: dict[str, list]

    def __init__(self, collection: Collection) -> None:
        """
         Initialize the instance. This is the method that must be called by the user to initialize the instance.
         
         @param collection - The collection of documents to operate on. If this is None the instance will be initialized with all documents in the collection
        """
        self.__collection = collection

        self.__process()

    def __process(self):
        """
         Process Guids @todo this needs to be refactored to use self. __parseGuids
        """
        self.__parseGuids()

    def __parseGuids(self):
        """
         Parse Guid's and store them in self. __guids @todo this needs to be
        """
        self.__guids = dict({"tmdb": list(), "tvdb": list(), "imdb": list()})

        # Add guids to the guids.
        for item in self.__collection.items():
            pih = PlexVideoHelper(item)

            # Add guids to the list of guids.
            for key in self.__guids.keys():
                self.__guids[key].append(pih.getGuidByName(key))

    def getGuidByName(self, name: str) -> list | None:
        """
         Get GUID by name. This is used to find the GUID that corresponds to a given name. If there is no such GUID None is returned
         
         @param name - Name of the GUID to look up
         
         @return List of GUIDs or None if not found ( in which case None is returned ) Note : The GUIDs are sorted by
        """
        return self.__guids[name] if name in self.__guids.keys() else None

    def getCollectionLabels(self) -> list[str] | None:
        return PlexItemHelper.getNamedCollectionLabels(self.__collection)
    
    @property
    def guids(self) -> dict[str, list]:
        """
         Returns the guids of the entity. This is a dictionary where keys are entity names and values are lists of GUIDs.
         
         
         @return the guids of the entity in the form of a dictionary where keys are entity names and values are lists of GUID
        """
        return self.__guids


class PlexVideoHelper:
    __item: PlexPartialObject
    __guids: dict[str, str]

    def __init__(self, item: PlexPartialObject):
        """
         Initialize the PlexPartialObject with data. This is called by __init__ and should not be called directly
         
         @param item - The item to be
        """
        self.__item = item
        self.__guids = {}

        self.__process()

    def __process(self):
        """
         Process Guids @todo this needs to be refactored to use self. __parseGuids
        """
        self.__parseGuids()

    def __parseGuids(self):
        """
         Parse guids and return a dictionary of guids. This is used to determine which items are part of the
        """
        try:
            # Set guids to a dict of guids
            if "guids" in self.__item.__dict__:
                self.__guids = dict(o.id.split("://") for o in self.__item.guids)
        except:
            pass

        try:
            # If the guid is not in the dict__ then the guid is replaced with the tvdb.
            if "guid" in self.__item.__dict__ and not self.__guids:
                # "guid": "com.plexapp.agents.thetvdb://73546?lang=en",
                try:
                    if self.__item.guid.startswith("com.plexapp.agents.thetvdb://"):
                        self.__guids["tvdb"] = self.__item.guid.replace(
                            "com.plexapp.agents.thetvdb://", ""
                        )

                    if self.__item.guid.startswith("com.plexapp.agents.themoviedb://"):
                        self.__guids["tmdb"] = self.__item.guid.replace(
                            "com.plexapp.agents.themoviedb://", ""
                        )

                    # If tvdb is not present in the guids tvdb then it will be removed from the guids tvdb.
                    if "?" in self.__guids["tvdb"]:
                        self.__guids["tvdb"] = str(self.__guids["tvdb"]).split("?")[0]

                    # If tvdb is not present in the guids tvdb then it will be removed from the guids tmdb.
                    if "?" in self.__guids["tmdb"]:
                        self.__guids["tmdb"] = str(self.__guids["tmdb"]).split("?")[0]
                except:
                    pass
        except:
            pass

        # Set the guid to the tmdb guid
        if "tmdb" not in self.__guids:
            self.__guids["tmdb"] = ""
        # Clear the guids for tvdb.
        if "tvdb" not in self.__guids:
            self.__guids["tvdb"] = ""
        # If imdb is not set this will remove the imdb guid from the guids
        if "imdb" not in self.__guids:
            self.__guids["imdb"] = ""

    def getGuidByName(self, name: str) -> str | None:
        """
         Get GUID by name. This is used to find the GUID that corresponds to a given entity name.
         
         @param name - Name of entity to look up. E. g.
         
         @return GUID or None if not found ( name not found ). Note that GUIDs are unique in the entity
        """
        return self.__guids[name] if name in self.__guids.keys() else None

    def getCollectionLabels(self) -> list[str] | None:
        return PlexItemHelper.getNamedCollectionLabels(self.__item)
    
    @property
    def guids(self) -> dict[str, str]:
        """
         Returns the guids of the entity. This is a dictionary with keys that correspond to the entity's GUID and values that correspond to the entity's name.
         
         
         @return the guids of the entity as a dictionary with keys that correspond to the entity's GUID and values that correspond
        """
        return self.__guids
