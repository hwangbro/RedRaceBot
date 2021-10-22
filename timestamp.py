from pyparsing import QuotedString, Regex
import sys
from dataclasses import dataclass

@dataclass
class Timestamp:
    '''Class representing a timestamp for a race split

    There are two components to the timestamp: the split name
    and the actual time. This class parses out different forms
    of time, and also keeps track of whether or not it was a real
    split or a skipped/undo. In the latter cases, the timestamp
    is set to sys.maxsize to push it to the bottom of sorting for
    race standings
    '''

    split_name: str = ''
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    ms: int = 0

    @property
    def total_ms(self) -> int:
        '''Returns the timestamp as milliseconds'''
        return self.ms + self.seconds*1000 + self.minutes*60*1000 + self.hours*60*60*1000

    @property
    def time_string(self) -> str:
        '''Returns the timestamp portion of the string representation'''
        ret = ''
        if self.hours:
            ret += f'{self.hours:02}:'
        ret += f'{self.minutes:02}:{self.seconds:02}.{self.ms//10:02}'

        return ret

    def __repr__(self):
        if self.split_name:
            return f'[{self.split_name}]: {self.time_string}'
        return self.time_string

class BlankTimestamp(Timestamp):
    '''Represents a "default" empty timestamp'''
    @property
    def total_ms(self) -> int:
        return sys.maxsize - 1

    @property
    def time_string(self) -> str:
        return 'N/A'

class ForfeitTimestamp(Timestamp):
    '''Represents a "forfeit" timestamp'''
    @property
    def total_ms(self) -> int:
        return sys.maxsize

    @property
    def time_string(self) -> str:
        return 'Forfeit'

class SkipTimestamp(Timestamp):
    '''Represents a skipped split timestamp'''
    @property
    def total_ms(self) -> int:
        return sys.maxsize-2

    @property
    def time_string(self) -> str:
        return 'Skipped'

def parse_timestamp(text) -> Timestamp:
    # !time RealTime "Lance" 1:57:22.20
    # !time RealTime "Lance" -
    # !done RealTime 2:00:20.78
    split_name = QuotedString('"').setResultsName('split_name')
    split_time = Regex(r'((?P<undo>-)|((?P<hours>\d?\d):)?(?P<minutes>\d?\d):(?P<seconds>\d\d)\.(?P<ms>\d\d))')
    split_msg = "RealTime" + split_name + split_time
    done_msg = "RealTime" + split_time

    parsed = list(split_msg.scanString(text))
    if not parsed:
        parsed = list(done_msg.scanString(text))
    if parsed:
        res = parsed[0][0]
        split_name = res.split_name if res.split_name else "Done"
        if res.undo:
            return SkipTimestamp(split_name)
        hours = 0
        if res.hours:
            hours = int(res.hours)
        minutes = int(res.minutes)
        seconds = int(res.seconds)
        ms = int(res.ms)*10
        return Timestamp(split_name, hours, minutes, seconds, ms)
