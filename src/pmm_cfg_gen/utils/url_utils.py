
# #!/usr/bin/env python3
# ###################################################################################################

# import logging
# from plexapi.base import PlexObject, PlexPartialObject
# from pmm_cfg_gen.utils.settings_yml import globalSettingsMgr
# from pmm_cfg_gen.utils.plex_utils import PlexItemHelper

# ###################################################################################################

# class UrlProcessor:
#     _baseUrl : str | None
#     _logger : logging.Logger
#     _itemHelper : PlexItemHelper
    
#     def __init__(self, baseUrl : str | None = None) -> None:
#         self._logger = logging.getLogger("pmm-cfg-gen")

#         self._baseUrl = baseUrl
        
#         pass

#     def generate(self, item) -> str | None:
#         self._processItem(item)

#         pass 

#     def generateCollectionSearchUrl(self, item) -> str | None:
#         self._processItem(item)

#         pass 

#     def generateItemSearchUrl(self, item) -> str | None:
#         self._processItem(item)

#         pass 

#     def _processItem(self, item : PlexPartialObject):
#         self._itemHelper = PlexItemHelper(item)

# ###################################################################################################

# class ThePosterDatabaseUrlProcessor(UrlProcessor):
#     def __init__(self, baseUrl: str | None = None) -> None:
#         super().__init__(baseUrl)

#     def generate(self, item) -> str | None:
#         return super().generate(item)

#     def generateCollectionSearchUrl(self, item) -> str | None:
#         return super().generateCollectionSearchUrl(item)

#     def generateItemSearchUrl(self, item) -> str | None:
#         return super().generateItemSearchUrl(item)

# ###################################################################################################

# class TheMovieDatabaseUrlProcessor(UrlProcessor)
#     def __init__(self, baseUrl: str | None = None) -> None:
#         super().__init__(baseUrl if baseUrl is not None else globalSettingsMgr.settings.theMovieDatabase.url )

#     def generate(self, item) -> str | None:
#         return super().generate(item)

#     def generateCollectionSearchUrl(self, item) -> str | None:
#         return super().generateCollectionSearchUrl(item)

#     def generateItemSearchUrl(self, item) -> str | None:
#         return super().generateItemSearchUrl(item)

# ###################################################################################################

# class TheTvDatabaseUrlProcessor(UrlProcessor):
#     def __init__(self, baseUrl: str | None = None) -> None:
#         super().__init__(baseUrl)

#     def generate(self, item) -> str | None:
#         return super().generate(item)

#     def generateCollectionSearchUrl(self, item) -> str | None:
#         return super().generateCollectionSearchUrl(item)

#     def generateItemSearchUrl(self, item) -> str | None:
#         return super().generateItemSearchUrl(item)

# ###################################################################################################

# class ImDbDatabaseUrlProcessor(UrlProcessor):
#     def __init__(self, baseUrl: str | None = None) -> None:
#         super().__init__(baseUrl)

#     def generate(self, item) -> str | None:
#         return super().generate(item)

#     def generateCollectionSearchUrl(self, item) -> str | None:
#         return super().generateCollectionSearchUrl(item)

#     def generateItemSearchUrl(self, item) -> str | None:
#         return super().generateItemSearchUrl(item)
