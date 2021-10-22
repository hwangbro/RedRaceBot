from timestamp import Timestamp
import srlapi
from trackedsplits import TrackedSplit, RBYSplits
from runner import Runner, RunnerSet
import cfg
import blacklist
import race_db
import logging
import asyncio

logger = logging.getLogger('main')

class Race:
    '''Class representation of a race tracked by the bot

    The race initializes with race data from the API. It also has two IRC
    listeners, one to communicate with twitch users, and one to listen to the
    SRL livesplit irc for split information.
    '''

    def __init__(self, race_id, bot=None):
        self.bot = bot
        self.race_id = race_id
        self.announced_splits = []
        self.srl = None
        self.standings = ''
        self.srl_livesplit_ch_name = f'srl-{self.race_id}-livesplit'
        self.tracked_splits = RBYSplits()
        self.finished = False
        self.silenced = False

        self.spoiler = False
        self.watch_msg = None
        self.announcement_msg = None

        self.runners = RunnerSet()
        self.twitch_irc_watchers = set()

    @property
    def multitwitch_link(self) -> str:
        base_url = 'https://multitwitch.tv/'
        runner_list = sorted(self.runners, key=lambda x: x.name.lower())
        for runner in runner_list:
            if runner.twitch_user and not runner.forfeit:
                base_url += f'{runner.twitch_user}/'

        return base_url

    @property
    def user_info(self) -> str:
        runner_info = 'Runner info | '
        runner_list = sorted(self.runners, key=lambda x: x.name.lower())
        for runner in runner_list:
            runner_info += f'{runner.name} - twitch.tv/{runner.twitch_user} | '
        return runner_info

    async def update_race(self) -> None:
        '''Updates the internal runners data

        This function is called whenever a livesplit event happens. It calls
        the SRL api to add any new runners, then updates the state of these
        runners, as well as refreshes the watcher status
        '''

        # maybe add even if they aren't found in srl?
        if new_race_data := srlapi.get_single_race(self.race_id):
            logger.info('Updating race')
            announce = await self._update_runners(new_race_data.entrants)
            if announce and not self.finished:
                logger.info('Check for announcing splits from updating race')
                await self._check_all_splits_announcement()
        else:
            logger.warning('Unable to update race')

    async def _update_runners(self, srl_data: dict) -> bool:
        '''Updates the SRL data for runners.

        Returns True if a runner's status changed to forfeited so the bot knows
        whether or not it should try announcing splits.
        '''
        # handle people leaving the race before it starts
        for runner in list(self.runners):
            if runner.name not in srl_data:
                self.runners.remove(runner)
                logger.info(f'removing user from race before it began: {runner.name}')
                if runner.twitch_user in self.twitch_irc_watchers:
                    self.twitch_irc_watchers.discard(runner.twitch_user)
                    await self.bot.twitch_irc._part(runner.twitch_user)
                    logger.info(f'removing user from watcher: {runner.twitch_user}')

        announce = False
        for name, data in srl_data.items():
            if not (runner := self.runners.get(name)):
                logger.info(f'Adding entrant {name} to race.')
                runner = Runner(data)
                self.runners.add(runner)

            # check if status changed to ff
            # if status goes from ff to non ff, add back to race?
            runner_ff = runner.forfeit
            runner.update_status(data.statetext)
            runner.message = data.message

            # Update blacklists and leaves/joins twitch channels
            if runner.twitch_user and not self.finished:
                await self._update_irc_watchers(runner.twitch_user, data.statetext)
            if not runner_ff and runner.forfeit:
                # Check for announcing splits if someone forfeits
                announce = True

        return announce

    async def _update_irc_watchers(self, twitch_user: str,
                                  statetext: str) -> None:

        blacklisted = blacklist.check_user(twitch_user)
        if blacklisted or statetext == 'Forfeit':
            if twitch_user in self.twitch_irc_watchers:
                logger.info(f'removing user from watcher: {twitch_user}')
                await self.bot.twitch_irc._part(twitch_user)
                self.twitch_irc_watchers.discard(twitch_user)
        else:
            if not blacklisted and twitch_user not in self.twitch_irc_watchers:
                logger.info(f'adding user to watcher: {twitch_user}')
                await self.bot.twitch_irc._join(twitch_user)
                self.twitch_irc_watchers.add(twitch_user)

    async def add_time(self, user: str, time_data: Timestamp) -> None:
        '''Core function to handle tracking split data.

        This function handles parsing and storing split data from livesplit.
        It appropriately handles skipped/undone splits, as well as controlling
        when splits should be announced to everybody when finished.
        '''

        split_data = self.tracked_splits[time_data.split_name]
        if not split_data:
            logger.info(f'Could not process split {time_data.split_name}')
            return

        await self.update_race()

        self.runners.add_split_time(user, split_data, time_data)
        await self._check_subset_announcement(split_data)
        await self._check_split_announcement(split_data)

    async def _check_subset_announcement(self, tracked_split) -> None:
        '''Handles checking and announcing subset watchers.

        This function iterates through all its runners and checks if the given
        split should be announced for that runner
        '''

        runners = self.runners.check_subset_announce(tracked_split)
        for runner in runners:
            runner_set = {self.runners.get(name) for name in runner.watched_runners}
            await self._announce_split(tracked_split, runner_set, {runner.twitch_user}, True)

    async def _check_split_announcement(self, tracked_split) -> None:
        '''Checks the given split and announce if ready.'''
        announce, finish = self.runners.check_global_announce(tracked_split)
        if finish:
            await self._handle_finish_race()
        elif announce:
            await self._announce_split(tracked_split, self.runners, self.twitch_irc_watchers)

    async def _check_all_splits_announcement(self) -> None:
        '''Calls _check_split_announcement on all splits.'''
        for tracked_split in self.tracked_splits:
            if tracked_split.Name not in self.announced_splits:
                await self._check_split_announcement(tracked_split)

    async def finish_race_for_user(self, user: str, time_data: Timestamp) -> None:
        '''Handles the 'Done' split for a user

        If all racers are finished (forfeit or completed), the race should be
        marked as finished and the racebot should no longer track the race or
        listen for inputs.
        '''

        split_data = self.tracked_splits['Done']
        self.runners.finish_user(user, split_data, time_data)
        await self._check_subset_announcement(split_data)

        if self.runners.finished:
            await self._handle_finish_race()

    async def _handle_finish_race(self) -> None:
        '''Finish race routine.

        Handles announcing the final split, posting results to Discord,
        cleaning up IRCs, and marking race as finished in the database.
        '''

        tracked_split = self.tracked_splits['Done']
        await self._announce_split(tracked_split, self.runners,
                                  self.twitch_irc_watchers)
        self.finished = True

        await self.disconnect_ircs()
        race_db.update_race(self.race_id, True)

        # Post results to discord
        standings = f'Race {self.race_id} results:\n\n{self.runners.standings(self.spoiler)}'
        try:
            await self.bot.send_message(standings, cfg.RACE_BOT_CHANNEL_ID)
            self.announcement_msg = await self.bot.send_message(standings, cfg.RED_RACE_CHANNEL_ID)

            for _ in range(2):
                logger.info('Sleeping for 60 seconds before updating comments')
                await asyncio.sleep(60)
                await self.update_race_comments()

        except Exception as e:
            logger.info(f'Failed to send message: {str(e)}')

    async def disconnect_ircs(self) -> None:
        '''Disconnects from all current irc channels'''
        for twitch_ch in self.twitch_irc_watchers:
            if not await self.bot.check_race_for_watcher(twitch_ch, self.race_id):
                logger.info(f'Leaving channel: {twitch_ch}')
                await self.bot.twitch_irc._part(twitch_ch)
        logger.info(f'Leaving SRL channel: {self.srl_livesplit_ch_name}')
        await self.bot.srl_irc._part(self.srl_livesplit_ch_name)

    async def _announce_split(self, split: TrackedSplit, runners: set[Runner],
                             watchers: set[str], subset=False) -> None:
        '''Announces split to the subset of runners'''
        if split in self.announced_splits:
            logger.info(f'Split {split.Name} has already been announced.')
            return

        times_str = self.runners.split_standings(split, runners)

        for chat in watchers:
            if self.silenced:
                logger.info(f'Skipping sending {times_str} to {chat} due to being silenced.')
            elif blacklist.check_user(chat):
                logger.info(f'Skipping sending {times_str} to {chat} due to being blacklisted.')
            else:
                logger.info(f'[{self.race_id}] Announcing split {split.Name} in {chat}\'s chat')
                await self.bot.twitch_irc.send(times_str, chat)

        if not subset:
            # only mark the split as announced if it's globally sent and not a subset
            self.announced_splits.append(split)

    async def add_external_watcher(self, watcher) -> bool:
        '''Adds a twitch channel to the watcher list.

        The channels added to this list might not be part of a race, but should
        still recieve split updates and query standings.
        '''

        added = False
        if not blacklist.check_user(watcher) and watcher not in self.twitch_irc_watchers:
            logger.info(f'adding external user to watcher: {watcher}')
            await self.bot.twitch_irc._join(watcher)
            self.twitch_irc_watchers.add(watcher)
            added = True

        return added

    async def update_race_comments(self) -> None:
        '''Updates the race result message with comments'''
        await self.update_race()
        standings = f'Race {self.race_id} results:\n\n{self.runners.standings(self.spoiler)}'
        if self.announcement_msg:
            await self.announcement_msg.edit(content=standings)
