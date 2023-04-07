#!/usr/bin/env python3
#######################################################################

import datetime 
import time 

#######################################################################

class timespan:
    __maxWeeks: int = 99999999999

    __totalTimeInSeconds : float

    __weeks : int
    __days : int 
    __hours : int
    __minutes : int 
    __seconds : float 
    
    def __init__(self, weeks : int | None = None,  days : int | None = None, hours : int | None = None, minutes : int | None = None, seconds : float | None = None, dt : datetime.datetime | None = None, time : float | None = None, timedelta : datetime.timedelta | None = None ) -> None:
        self.__totalTimeInSeconds = 0
        self.__weeks = 0
        self.__days = 0
        self.__hours = 0
        self.__minutes = 0
        self.__seconds = 0
        
        if weeks: self.add_weeks(weeks)
        if days: self.add_days(days) 
        if hours: self.add_hours(hours)
        if minutes: self.add_minutes(minutes)
        if seconds: self.add_seconds(seconds)
        if dt: self.add_datetime(dt)
        if time: self.add_time(time)

    def add_weeks(self, weeks: int):
        self.add_days(weeks * 7)

        return self 

    def add_days(self, days : int):
        self.add_hours(days * 24)

        return self 

    def add_hours(self, hours: int):
        self.add_minutes(hours * 60)

        return self 

    def add_minutes(self, minutes: int):
        self.add_seconds(minutes * 60)

        return self 

    def add_seconds(self, seconds: float):
        self.__totalTimeInSeconds += seconds

        self.__refresh()

        return self 

    def add_datetime(self, dt : datetime.datetime):
        self.add_seconds((dt - datetime.datetime(1970, 1, 1)).total_seconds())

        return self 

    def add_time(self, time : float):
        self.add_seconds(time)

        return self 

    def to_dict(self):
        return {
            "weeks": self.__weeks,
            "days": self.__days,
            "hours": self.__hours,
            "minutes": self.__minutes,
            "seconds": self.__seconds,
            "totalTimeInSeconds": self.__totalTimeInSeconds
        }

    def to_str(self):       
        return ', '.join('%d %s' % (num, unit)
		     for num, unit in zip([(self.total_seconds // d) % m
					   for d, m in ((604800, self.__maxWeeks), 
                                                        (86400, 7), (3600, 24), 
                                                        (60, 60), (1, 60))],
					  ['wk', 'd', 'hr', 'min', 'sec'])
		     if num)
 
    def __refresh(self):       
        result = [(num, unit) for num, unit in zip([(self.__totalTimeInSeconds // d) % m
					   for d, m in ((604800, self.__maxWeeks), 
                                                        (86400, 7), (3600, 24), 
                                                        (60, 60), (1, 60))],
					  ['wk', 'd', 'hr', 'min', 'sec'])
        ]

        #result.reverse()

        self.__seconds = result.pop()[0]
        self.__minutes  = int(result.pop()[0])
        self.__hours = int(result.pop()[0])
        self.__days  = int(result.pop()[0])
        self.__weeks = int(result.pop()[0])
   
    @property
    def weeks(self): return self.__weeks
    
    @property
    def days(self): return self.__days
    
    @property
    def hours(self): return self.__hours

    @property
    def minutes(self): return self.__minutes
    
    @property
    def seconds(self): return self.__seconds

    @property
    def total_seconds(self): return self.__totalTimeInSeconds

def time_span_tests():
    dt1 = datetime.datetime.now()
    dt2 = datetime.datetime.now() - datetime.timedelta(hours=1, minutes=5)

    ts = timespan(seconds=(dt1 - dt2).total_seconds())

    print("dt1: {}".format(dt1))
    print("dt2: {}".format(dt2))
    print(ts.to_dict())
    print(ts.to_str())

    ts.add_weeks(1)

    print(ts.to_dict())
    print(ts.to_str())

if __name__ == "__main__":
    time_span_tests()