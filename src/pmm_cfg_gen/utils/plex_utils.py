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