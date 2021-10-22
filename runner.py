from srlmodels import SRLEntrant
from trackedsplits import TrackedSplit
from timestamp import SkipTimestamp, Timestamp, BlankTimestamp, ForfeitTimestamp
from typing import Tuple
import logging

logger = logging.getLogger('main')

class Runner:
    '''Represents a runner in a race.

    This class holds data relevant to a runner in a given race. It tracks data
    such as their entrant info from SRL, as well as race specific data like
    split times and forfeit status.
    '''

    def __init__(self, srl_data: SRLEntrant):
        self.splits = {} # key = trackedSplit, value = timestamp
        self.srl_data = srl_data
        self.name = self.srl_data.displayname
        self.twitch_user = self.srl_data.twitch.lower()
        self.forfeit = srl_data.statetext == 'Forfeit'
        self.message = srl_data.message
        self.finished = False
        self.watched_runners = set() # str
        self.ignored = False
        self.announced_watched_splits = set() # trackedsplit

    def update_status(self, statetext: str) -> None:
        self.forfeit = statetext == 'Forfeit'
        if self.forfeit:
            self.finished = True

    def add_split(self, split: TrackedSplit, time: Timestamp) -> None:
        self.splits[split] = time

    def undo_split(self, split: TrackedSplit) -> None:
        del self.splits[split]

    @property
    def latest_split(self) -> Tuple[TrackedSplit, Timestamp]:
        '''Returns the latest split that the user has completed.

        Skipped splits count as completed, and the order is determined by the
        position of the TrackedSplit in self.splits.

        If the user is forfeit, return a "forfeit" split.
        '''

        split = ts = None
        if self.forfeit:
            split = TrackedSplit(-1, 'Forfeit')
            ts = ForfeitTimestamp()
            # ts = Timestamp('Forfeit', True)
        else:
            splits = [x for x in self.splits.keys() if not isinstance(self.get_split_time(x), SkipTimestamp)]

            if highest_key := sorted(splits, key=lambda x: x.Position, reverse=True):
                highest_key = highest_key[0]
                split = highest_key
                ts = self.splits[highest_key]
            else:
                # default to sending blank split if user has not FF but no split exists
                split = TrackedSplit(0, 'N/A')
                ts = BlankTimestamp()

        return split, ts

    @property
    def latest_split_order(self) -> Tuple[int, int, str]:
        '''Ordering mechanism for sorting racers by their latest split

        Returns the Split Position, time in MS, and the runners name.
        '''
        split, ts = self.latest_split
        return split.Position * -1, ts.total_ms, self.name

    def split_order(self, split: TrackedSplit) -> Tuple[int, str]:
        '''Ordering mechanism for sorting racers with a defined split

        Returns the Split Position, time in MS, and the runners name.
        '''
        return self.get_split_time(split).total_ms, self.name

    def get_split_time(self, split: TrackedSplit) -> Timestamp:
        '''Returns the Timestamp for a given TrackedSplit

        Returns None if the user has not finished the split.
        If the user has forfeited the race, they should have every split be
        marked as N/A, and the Timestamp would be sys.maxsize so that when
        ordered by time, they would appear at the bottom along with other
        skipped/forfeited runners
        '''

        if self.forfeit:
            return ForfeitTimestamp()
        if self.ignored:
            return BlankTimestamp()
        if split in self.splits:
            return self.splits[split]

    def completed_split(self, split: TrackedSplit) -> bool:
        '''Returns True if the runner has completed the split'''
        return split in self.splits

    def user_matches(self, name: str) -> bool:
        '''Returns true if a name matches this user's twitch or display name'''
        return name.lower() in {self.name.lower(), self.twitch_user.lower()}

    def announcement_standing_str(self, split: TrackedSplit) -> str:
        '''Creates the announcement standing text'''
        split_time = self.get_split_time(split).time_string
        return f'{self.name} - {split_time}'

    def latest_standing_str(self, race_finished=False, comments=False) -> str:
        '''Creates the latest standing text'''
        split, ts = self.latest_split
        split_details = f'{ts.time_string}'

        if type(ts) == Timestamp and not race_finished:
            split_details = f'{split.Name} {ts.time_string}'
        if race_finished and not self.finished:
            split_details = 'N/A'

        split_details = f'({split_details})'

        if comments and self.message:
            split_details = f'{split_details} ({self.message})'

        return f'{self.name}: {split_details}'

    def __repr__(self) -> str:
        return f'Runner: {self.twitch_user}, Status: {self.forfeit}'

class RunnerSet(set):
    @property
    def finished(self) -> bool:
        '''Returns True if all the runners are finished'''
        return all(runner.forfeit or runner.finished for runner in self)

    def get(self, name) -> Runner:
        '''Returns a runner if it matches the given alias'''
        return next((runner for runner in self if runner.user_matches(name)), None)

    def user_ignore(self, user: str, ignore: bool) -> bool:
        '''Returns True if user was found'''

        if runner := self.get(user):
            runner.ignored = ignore
            return True
        return False

    def split_is_complete(self, tracked_split: TrackedSplit,
                          runner_subset: set[Runner]=set()) -> bool:
        '''Returns True if the split is finished for the subset of runners

        A split is considered finished if they have a split for it, if they
        forfeited, or if they are ignored.
        '''

        if not runner_subset:
            runner_subset = self
        return all([x.completed_split(tracked_split) or x.forfeit or x.ignored for x in runner_subset])

    def add_split_time(self, user: str, split_data: TrackedSplit,
                       time_data: Timestamp) -> None:
        '''Core function to handle tracking split data.

        This function handles parsing and storing split data from livesplit.
        It appropriately handles skipped/undone splits.
        '''

        if runner := self.get(user):
            if type(time_data) == Timestamp:
                runner.add_split(split_data, time_data)
                logger.info(f'Adding split {split_data.Name} - {time_data} for runner {runner.name}')
            else:
                if split_data in runner.splits:
                    runner.undo_split(split_data)
                    logger.info(f'Runner {runner.name} undid split {split_data.Name}')
                else:
                    runner.add_split(split_data, time_data)
                    logger.info(f'Runner {runner.name} skipped split {split_data.Name}')

    def finish_user(self, user: str, split_data: TrackedSplit,
                    time_data: Timestamp):
        '''Handles the Done split for a user'''
        if isinstance(time_data, SkipTimestamp):
            return

        if runner := self.get(user):
            runner.add_split(split_data, time_data)
            runner.finished = True
            runner.ignored = False
            logger.info(f'Finish race for runner {runner.name} - {time_data}')

    def check_subset_announce(self, tracked_split: TrackedSplit) -> set[Runner]:
        '''Returns set of runners to announce subsets'''
        announce = set()
        for runner in self:
            if runner.watched_runners and not runner.forfeit:
                if tracked_split.Name not in runner.announced_watched_splits:
                    subset_runners = {self.get(name) for name in runner.watched_runners}
                    if self.split_is_complete(tracked_split, subset_runners):
                        runner.announced_watched_splits.add(tracked_split.Name)
                        announce.add(runner)

        return announce

    def check_global_announce(self, tracked_split: TrackedSplit) -> Tuple[bool, bool]:
        '''Checks if you should globally announce a split

        Returns a pair of bools in a tuple, one if you should announce the
        split, another if the race is finished
        '''
        announce, finish = False, False
        if announce := self.split_is_complete(tracked_split):
            if tracked_split.Name == 'Done' and self.finished:
                finish = True

        return announce, finish

    def watchlist(self, watcher: str) -> set[str]:
        '''Returns the watchlist for a given watcher'''
        if runner := self.get(watcher):
            return runner.watched_runners

    def reset_watchlist(self, watcher: str) -> None:
        '''Resets the watchlist for a given watcher'''
        if runner := self.get(watcher):
            runner.watched_runners = set()

    def set_watchlist(self, watcher: str, runners: str) -> set[str]:
        '''Sets the watchlist for a given watcher

        Input is a comma separated list of names
        '''
        if target := self.get(watcher):
            watched_runners = set()
            for runner_name in runners.split(','):
                runner_name = runner_name.strip()
                if runner := self.get(runner_name):
                    if runner.twitch_user:
                        watched_runners.add(runner.twitch_user)

            logger.info(f'Updating watcher list for {target.name} to {watched_runners}')
            target.watched_runners = watched_runners
            return watched_runners

    def standings(self, spoiler: bool) -> str:
        '''Returns the current race standing string'''
        placements = '\n'.join(self.overall_standings_list(True, True))
        if spoiler:
            placements = '||' + placements + '||'
        return placements

    def overall_standings_list(self, finished=False, comments=False) -> list[str]:
        '''Calculates the current standings

        Returns a list of placements strings in order to be consumed by
        different functions and formatted independently
        '''
        sorted_runners = list(self)
        sorted_runners.sort(key=lambda x: x.latest_split_order)

        standings = []
        for idx, runner in enumerate(sorted_runners):
            place = idx + 1
            split_details = runner.latest_standing_str(finished, comments)
            if runner.forfeit or (finished and not runner.finished):
                place = 'N/A'

            standings.append(f'{place}. {split_details}')

        return standings

    def split_standings(self, split: TrackedSplit, runners: set[Runner]) -> str:
        '''Gets the split standings for a given split and a subset of runners'''
        runner_list = sorted([r for r in runners if r.get_split_time(split)],
                             key=lambda x: x.split_order(split))

        times_str = f'{split.Name} split standings: '
        for idx, runner in enumerate(runner_list):
            place = 'N/A' if runner.forfeit else idx + 1
            times_str += f'{place}. {runner.announcement_standing_str(split)}. '

        return times_str.strip()
