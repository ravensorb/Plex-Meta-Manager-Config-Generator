#!/usr/bin/env python3
###################################################################################################

# from datetime import timedelta
# import time
import json

import jsonpickle
from pmm_cfg_gen.utils.timer import timer

###################################################################################################

class PlexStatsTotals:
    total: int
    processed: int
    skipped: int

    def __init__(self) -> None:
        self.total = 0
        self.processed = 0
        self.skipped = 0
        self.percentage = 0

    def _addStats(self, stats):
        self.total += stats.total
        self.processed += stats.processed
        self.skipped += stats.skipped

    def calcPercentage(self):
        if self.total > 0:
            self.percentage = int(self.processed / self.total * 100)

    def toJson(self):
        return {
            "total": self.total,
            "processed": self.processed,
            "skipped": self.skipped,
            "percentage": self.percentage,
        }

class PlexStatsLibraryTotals:
    totals: PlexStatsTotals

    collections: PlexStatsTotals
    items: PlexStatsTotals

    def __init__(self) -> None:
        self.totals = PlexStatsTotals()
        self.collections = PlexStatsTotals()
        self.items = PlexStatsTotals()

    def calcTotals(self):
        self.totals.total = self.collections.total + self.items.total
        self.totals.processed = self.collections.processed + self.items.processed
        self.totals.skipped = self.collections.skipped + self.items.skipped

        self.totals.calcPercentage()
        self.collections.calcPercentage()
        self.items.calcPercentage()

    def toJson(self):
        return {
            "totals": self.totals.toJson(),
            "collections": self.collections.toJson(),
            "videos": self.items.toJson(),
        }

class PlexStats:
    timerProgram: timer
    timerLibraries: dict[str, timer]

    countsProgram: PlexStatsLibraryTotals
    countsLibraries: dict[str, PlexStatsLibraryTotals]

    def __init__(self) -> None:
        self.timerProgram = timer()
        self.timerLibraries = {}

        self.countsProgram = PlexStatsLibraryTotals()
        self.countsLibraries = {}

    def initLibrary(self, libraryName: str):
        self.timerLibraries[libraryName] = timer()
        self.countsLibraries[libraryName] = PlexStatsLibraryTotals()

    def calcTotals(self):
        # for libraryName in self.timerLibraries.keys():
        #     pass

        for libraryName in self.countsLibraries.keys():
            self.countsLibraries[libraryName].calcTotals()

            self.countsProgram.collections._addStats(
                self.countsLibraries[libraryName].collections
            )
            self.countsProgram.items._addStats(self.countsLibraries[libraryName].items)

        self.countsProgram.calcTotals()

    def toJson(self):
        return {
            "timers": {
                "program": json.loads(str(jsonpickle.dumps(self.timerProgram, unpicklable=False))),
                "libraries": json.loads(str(jsonpickle.dumps(self.timerLibraries, unpicklable=False))),
            },
            "counts": {
                "program": json.loads(str(jsonpickle.dumps(self.countsProgram, unpicklable=False))),
                "libarlibrariesies": json.loads(str(jsonpickle.dumps(self.countsLibraries, unpicklable=False)))
            }
        }
