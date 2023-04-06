#!/usr/bin/env python3
###################################################################################################

import time

###################################################################################################


class PlexStatsTimer:
    __timerStart: float
    __timerEnd: float

    def start(self):
        self.__timerStart = time.perf_counter()

    def end(self):
        self.__timerEnd = time.perf_counter()

    @property
    def delta(self) -> float:
        return self.__timerEnd - self.__timerStart


class PlexStatsTotals:
    total: int
    processed: int

    def __init__(self) -> None:
        self.total = 0
        self.processed = 0

    def _addStats(self, stats):
        self.total += stats.total
        self.processed += stats.processed


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


class PlexStats:
    timerProgram: PlexStatsTimer
    timerLibraries: dict[str, PlexStatsTimer]

    countsProgram: PlexStatsLibraryTotals
    countsLibraries: dict[str, PlexStatsLibraryTotals]

    def __init__(self) -> None:
        self.timerProgram = PlexStatsTimer()
        self.timerLibraries = {}

        self.countsProgram = PlexStatsLibraryTotals()
        self.countsLibraries = {}

    def initLibrary(self, libraryName: str):
        self.timerLibraries[libraryName] = PlexStatsTimer()
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