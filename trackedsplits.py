from dataclasses import dataclass
from typing import Tuple

@dataclass(eq=True, frozen=True)
class TrackedSplit:
    '''Class that represents a split that the racebot should track.

    These splits are ones that racers should be matching in livesplit.
    They are ordered in a specific way, and have aliases for slight
    common variations between runners
    '''

    Position: int
    Name: str
    Aliases: Tuple[str] = ()

    def matches(self, name) -> bool:
        '''Returns True if the name matches or if it's an alias'''
        name = name.lower()
        exact_match = name == self.Name.lower()
        alias_match = name in {alias.lower() for alias in self.Aliases}
        return exact_match or alias_match

    def __repr__(self):
        return f'{self.Name} - Position: {self.Position}'

class TrackedSplits:
    '''Class represents the collection of TrackedSplits that make up a run'''
    def __init__(self):
        self.splits = []

    def __getitem__(self, name):
        if isinstance(name, int):
            return self.splits[name]
        split = [x for x in self.splits if x.matches(name)]
        if split:
            return split[0]

class RBYSplits(TrackedSplits):
    def __init__(self):
        super().__init__()
        self.splits.append(TrackedSplit(-1, 'Forfeit'))
        self.splits.append(TrackedSplit(0, 'N/A'))
        self.splits.append(TrackedSplit(1, 'Rival 1', ('Rival', 'Blue 1', 'Gary 1', 'Leave Lab')))
        self.splits.append(TrackedSplit(2, 'Nidoran', ('Nido', 'NidoranM')))
        self.splits.append(TrackedSplit(3, 'Brock'))
        self.splits.append(TrackedSplit(4, 'Route 3', ('Route 03', 'Rt 3', 'Rt. 3', 'Rt. 03')))
        self.splits.append(TrackedSplit(5, 'Mt. Moon', ('Mt Moon', 'Moon')))
        self.splits.append(TrackedSplit(6, 'Nugget Bridge', ('Bridge',)))
        self.splits.append(TrackedSplit(7, 'Misty'))
        self.splits.append(TrackedSplit(8, 'Surge', ('Lt Surge', 'Lt. Surge')))
        self.splits.append(TrackedSplit(9, 'Fly', ('HM02', 'HM 02', 'HM Fly')))
        self.splits.append(TrackedSplit(10, 'Flute', ('PokeFlute', 'Poke Flute')))
        self.splits.append(TrackedSplit(11, 'Koga'))
        self.splits.append(TrackedSplit(12, 'Erika'))
        self.splits.append(TrackedSplit(13, 'Blaine'))
        self.splits.append(TrackedSplit(14, 'Sabrina'))
        self.splits.append(TrackedSplit(15, 'Giovanni', ('Gio 2',)))
        self.splits.append(TrackedSplit(16, 'Lorelei'))
        self.splits.append(TrackedSplit(17, 'Bruno'))
        self.splits.append(TrackedSplit(18, 'Agatha'))
        self.splits.append(TrackedSplit(19, 'Lance'))
        self.splits.append(TrackedSplit(20, 'Champion', ('Champ', 'Blue')))
        self.splits.append(TrackedSplit(21, 'Hall of Fame', ('HoF', 'End'))) # redundant?
        self.splits.append(TrackedSplit(100, 'Done'))
