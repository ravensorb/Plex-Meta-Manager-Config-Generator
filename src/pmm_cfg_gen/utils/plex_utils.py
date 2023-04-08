#!/usr/bin/env python3
###################################################################################################

import logging

import jsonpickle
from plexapi.base import PlexObject, PlexPartialObject
from plexapi.server import PlexServer

from pmm_cfg_gen.utils.settings_yml import globalSettingsMgr

###################################################################################################

# jsonpickle.handlers.register(PlexObject, base=True)
class PlexJsonHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        pass

    def flatten(self, obj, data):
        # Fix url raise
        if isinstance(obj, PlexServer):
            setattr(obj, "_baseurl", globalSettingsMgr.settings.plex.serverUrl)
        # remove methods, private fields etc
        members = [
            attr
            for attr in dir(obj)
            if not callable(getattr(obj, attr))
            and not attr.startswith("__")
            and not attr.startswith("_")
        ]
        for normal_field in members:
            # we use context flatten - so its called handlers for given class
            data[normal_field] = self.context.flatten(getattr(obj, normal_field), {})
        return data

jsonpickle.handlers.registry.register(PlexObject, PlexJsonHandler, True)

###################################################################################################

def isPMMItem(item: PlexPartialObject):
    for label in item.labels:
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

        if str(item.title).strip() in [
            "Golden Globes Best Director Winners",
            "Golden Globes Best Picture Winners",
            "Oscars Best Director Winners",
            "Oscars Best Picture Winners",
            "Newly Released",
            "New Episodes",
            "TMDb Airing Today",
            "TMDb On The Air"
        ]:
            logging.getLogger("pmm_cfg_gen").debug(
                "isPMMItem Found: {} - {}".format(item.title, label.tag)
            )
            return True
            

    return False

def _cleanTitle(s: str) -> str:
    return s.replace("/", "-").replace("\\", "-")

def _formatItemTitle(item) -> str:
    s = " ({})".format(item.year)
    
    return "{}{}".format(item.title, s if s.strip() not in item.title else "")

###################################################################################################

class PlexItemHelper:
    __item : PlexPartialObject
    __guids : dict[str, str]
    
    def __init__(self, item : PlexPartialObject):
        self.__item = item
        self.__guids = {}

        self.__process()

    def __process(self):
        self.__parseGuids()

    def __parseGuids(self):
        if "guids" in self.__item.__dict__:
            self.__guids = dict(o.id.split("://") for o in self.__item.guids)

        if "guid" in self.__item.__dict__ and not self.__guids:
            #"guid": "com.plexapp.agents.thetvdb://73546?lang=en",
            try:
                s = self.__item.guid.replace("com.plexapp.agents.thetvdb://", "")
                self.__guids["tvdb"] = self.__item.guid.replace("com.plexapp.agents.thetvdb://", "")

                if "?" in self.__guids["tvdb"]:
                    self.__guids["tvdb"] = str(self.__guids["tvdb"]).split("?")[0]
            except:
                pass 

        if "tmdb" not in self.__guids: self.__guids["tmdb"] = ""
        if "tvdb" not in self.__guids: self.__guids["tvdb"] = ""
        if "imdb" not in self.__guids: self.__guids["imdb"] = ""               

    def getGuidByName(self, name : str) -> str | None:
        return self.__guids[name] if name in self.__guids.keys() else None

    @property
    def guids(self) -> dict[str, str]: return self.__guids