from enum import Enum
from dataclasses import dataclass

# maybe unnecessary
class RaceState(Enum):
    ENTRY_OPEN = 1
    ENTRY_CLOSED = 2
    IN_PROGRESS = 3
    COMPLETE = 4
    TERMINATED = 5

# entrant statetext
# "Entered", "Ready", "Finished", "Forfeit"

@dataclass
class SRLRace:
    id: str
    game: dict
    goal: str
    time: int
    state: RaceState
    statetext: str
    filename: str
    numentrants: int
    entrants: dict

    def __post_init__(self):
        self.state = RaceState(self.state)
        self.game = SRLGame(**self.game)
        entrants = dict()
        for name, entrant in self.entrants.items():
            entrants[name] = SRLEntrant(**entrant)
        self.entrants = entrants

    def summary_str(self) -> str:
        ret = f'{self.game.name} Race - {self.goal}, with {self.numentrants} racers: '
        ret += ', '.join([x.displayname for x in self.entrants.values()])

        ret += f'. Status: {self.statetext}'
        return ret

@dataclass
class SRLEntrant:
    '''Class representing entrant data from SRL's api'''

    displayname: str
    place: int
    time: int
    message: str
    statetext: str
    twitch: str
    trueskill: str

@dataclass
class SRLGame:
    '''Class representing game data from SRL's api'''

    id: int
    name: str
    abbrev: str
    popularity: int
    popularityrank: int
