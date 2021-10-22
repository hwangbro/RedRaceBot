import unittest
from unittest.mock import Mock
import asyncio

import bot
import race
import irc
from srlmodels import SRLRace
import blacklist
import srlapi
import race_db

import discord.ext.commands

class TestBot(unittest.TestCase):

    class MockContext:
        async def send(self, msg):
            pass

    class MockMessage:
        async def edit(self, *args, **kwargs):
            pass

    async def send_mock(self, msg, channel):
        pass

    async def basic_send_mock(self, msg):
        pass

    async def discord_send_mock(self, *args):
        return self.MockMessage()

    async def message_edit_mock(self, *args, **kwargs):
        pass

    async def update_race_mock(self):
        pass

    async def update_race_comments_mock(self):
        pass

    async def _check_all_splits_announcement_mock(self):
        pass

    async def _check_subset_announcement_mock(self, *args):
        pass

    async def _handle_finish_race_mock(self):
        pass

    async def init_ircs_mock(self, race_id):
        pass

    async def sleep_mock(self, *args, **kwargs):
        pass

    def setUp(self) -> None:
        self.discord_bot = bot.DiscordBot(None)
        self.loop = asyncio.get_event_loop()

        self._irc_send = irc.IRC.send
        irc.IRC.send = Mock(auto_spec=True, side_effect=self.send_mock)

        self._irc_basic_send = irc.IRC.basic_send
        irc.IRC.basic_send = Mock(auto_spec=True, side_effect=self.basic_send_mock)

        self._context = discord.ext.commands.Context
        discord.ext.commands.Context = Mock(auto_spec=True, side_effect=self.MockContext)

        self._discord_send = self.MockContext.send
        self.MockContext.send = Mock(auto_spec=True, side_effect=self.discord_send_mock)

        self._msg_edit = self.MockMessage.edit
        self.MockMessage.edit = Mock(auto_spec=True, side_effect=self.message_edit_mock)

        self._update_race_comments = race.Race.update_race_comments
        race.Race.update_race_comments = Mock(auto_spec=True, side_effect=self.update_race_comments_mock)

        self._update_race = race.Race.update_race
        race.Race.update_race = Mock(auto_spec=True, side_effect=self.update_race_mock)

        self._all_announcement = race.Race._check_all_splits_announcement
        race.Race._check_all_splits_announcement = Mock(auto_spec=True, side_effect=self._check_all_splits_announcement_mock)

        self._subset_announcement = race.Race._check_subset_announcement
        race.Race._check_subset_announcement = Mock(auto_spec=True, side_effect=self._check_subset_announcement_mock)

        self.__handle_finish_race = race.Race._handle_finish_race
        race.Race._handle_finish_race = Mock(auto_spec=True, side_effect=self._handle_finish_race_mock)

        self._init_ircs = bot.DiscordBot.init_ircs
        bot.DiscordBot.init_ircs = Mock(auto_spec=True, side_effect=self.init_ircs_mock)

        self._find_race = srlapi.find_race_with_user
        srlapi.find_race_with_user = Mock(auto_spec=True)

        self._sleep_mock = asyncio.sleep
        asyncio.sleep = Mock(auto_spec=True, side_effect=self.sleep_mock)

        self.context = discord.ext.commands.Context()

        race_dict = {'id': 'q7bsl', 'game': {'id': 6, 'name': 'Pokémon Red/Blue', 'abbrev': 'pkmnredblue', 'popularity': 382.0, 'popularityrank': 5
            }, 'goal': 'any% glitchless no it', 'time': 1624728151, 'state': 3, 'statetext': 'In Progress', 'filename': '', 'numentrants': 4, 'entrants':
                {'vidgmaddiict': {'displayname': 'vidgmaddiict', 'place': 1, 'time': 6945, 'message': '', 'statetext': 'Finished', 'twitch': 'vidgmaddiict', 'trueskill': '583'
                }, 'Yujito': {'displayname': 'Yujito', 'place': 2, 'time': 6946, 'message': '', 'statetext': 'Finished', 'twitch': 'yujitoo', 'trueskill': '434'
                }, 'Abdalain': {'displayname': 'Abdalain', 'place': 9994, 'time': -3, 'message': '', 'statetext': 'Ready', 'twitch': 'abdalain', 'trueskill': '575'
                }, 'Sidosh': {'displayname': 'Sidosh', 'place': 9998, 'time': -1, 'message': 'PC fucking restarted by itself, so I desperately tried to die cause I was so pissed that I became personal. Sry for any insults', 'statetext': 'Forfeit', 'twitch': 'sidosh', 'trueskill': '511'
                }
            }
        }
        self.race_data = SRLRace(**race_dict)
        self.race_id = 'q7bsl'
        self.race = race.Race(self.race_id, self.discord_bot)
        self.discord_bot.races[self.race_id] = self.race
        self.loop.run_until_complete(self.race._update_runners(self.race_data.entrants))

    def tearDown(self) -> None:
        irc.IRC.send.mock_reset()
        irc.IRC.send = self._irc_send

        irc.IRC.basic_send.mock_reset()
        irc.IRC.basic_send = self._irc_basic_send

        discord.ext.commands.Context.mock_reset()
        discord.ext.commands.Context = self._context

        self.MockContext.send.mock_reset()
        self.MockContext.send = self._discord_send

        self.MockMessage.edit.mock_reset()
        self.MockMessage.edit = self._msg_edit

        blacklist.remove_user('xd_bot_xd')
        race_db.delete_race(self.race_id)

        race.Race.update_race_comments.mock_reset()
        race.Race.update_race_comments = self._update_race_comments

        race.Race.update_race.mock_reset()
        race.Race.update_race = self._update_race

        race.Race._check_all_splits_announcement.mock_reset()
        race.Race._check_all_splits_announcement = self._all_announcement

        race.Race._check_subset_announcement.mock_reset()
        race.Race._check_subset_announcement = self._subset_announcement

        race.Race._handle_finish_race.mock_reset()
        race.Race._handle_finish_race = self.__handle_finish_race

        bot.DiscordBot.init_ircs.mock_reset()
        bot.DiscordBot.init_ircs = self._init_ircs

        asyncio.sleep.mock_reset()
        asyncio.sleep = self._sleep_mock

        srlapi.find_race_with_user.mock_reset()
        srlapi.find_race_with_user = self._find_race

    def test_init(self):
        self.assertTrue(self.discord_bot.twitch_irc.is_twitch)

    def test_watch(self):
        self.discord_bot.races.pop(self.race_id)
        srlapi.find_race_with_user.return_value = self.race_data
        self.loop.run_until_complete(self.discord_bot.watch(self.discord_bot, ctx=self.context, user='yujito'))
        exp_str = 'Found a race! ID: q7bsl\nPokémon Red/Blue Race - any% glitchless no it, with 4 racers: vidgmaddiict, Yujito, Abdalain, Sidosh. Status: In Progress\nThis race will now be tracked'
        self.MockMessage.edit.assert_called_once_with(content=exp_str)

    def test_watch_with_spoiler(self):
        self.discord_bot.races.pop(self.race_id)
        srlapi.find_race_with_user.return_value = self.race_data
        self.loop.run_until_complete(self.discord_bot.watch(self.discord_bot, self.context, 'yujito', 'spoiler'))
        exp_str = 'Found a race! ID: q7bsl\nPokémon Red/Blue Race - any% glitchless no it, with 4 racers: vidgmaddiict, Yujito, Abdalain, Sidosh. Status: In Progress\nThis race will now be tracked and marked as a spoiler'
        self.MockMessage.edit.assert_called_once_with(content=exp_str)

    def test_watch_with_silence(self):
        self.discord_bot.races.pop(self.race_id)
        srlapi.find_race_with_user.return_value = self.race_data
        self.loop.run_until_complete(self.discord_bot.watch(self.discord_bot, self.context, 'yujito', 'silent'))
        exp_str = 'Found a race! ID: q7bsl\nPokémon Red/Blue Race - any% glitchless no it, with 4 racers: vidgmaddiict, Yujito, Abdalain, Sidosh. Status: In Progress\nThis race will now be tracked silently'
        self.MockMessage.edit.assert_called_once_with(content=exp_str)

    def test_watch_with_spoiler_and_silence(self):
        self.discord_bot.races.pop(self.race_id)
        srlapi.find_race_with_user.return_value = self.race_data
        self.loop.run_until_complete(self.discord_bot.watch(self.discord_bot, self.context, 'yujito', 'silence', 'spoiler'))
        exp_str = 'Found a race! ID: q7bsl\nPokémon Red/Blue Race - any% glitchless no it, with 4 racers: vidgmaddiict, Yujito, Abdalain, Sidosh. Status: In Progress\nThis race will now be tracked silently and marked as a spoiler'
        self.MockMessage.edit.assert_called_once_with(content=exp_str)

    def test_add_watcher(self):
        self.assertEqual(irc.IRC.basic_send.call_count, 3)
        self.loop.run_until_complete(self.discord_bot.add_watcher(self.discord_bot, ctx=self.context, race_id='q7bsl', watcher='hwangbroxd'))
        self.context.send.assert_called_once_with('Added hwangbroxd as a watcher of q7bsl')
        irc.IRC.basic_send.assert_called_with('JOIN #hwangbroxd')

    def test_add_blacklisted_user(self):
        blacklist.add_user('xd_bot_xd')
        self.assertEqual(irc.IRC.basic_send.call_count, 3)
        self.loop.run_until_complete(self.discord_bot.add_watcher(self.discord_bot, ctx=self.context, race_id='q7bsl', watcher='xd_bot_xd'))
        self.context.send.assert_called_once_with('')
        self.assertEqual(irc.IRC.basic_send.call_count, 3)

    def test_update_comments(self):
        self.loop.run_until_complete(self.discord_bot.update_comments(self.discord_bot, ctx=self.context, race_id='q7bsl'))
        race.Race.update_race_comments.assert_not_called()

        self.discord_bot.races[self.race_id].finished = True
        self.loop.run_until_complete(self.discord_bot.update_comments(self.discord_bot, ctx=self.context, race_id='q7bsl'))
        race.Race.update_race_comments.assert_called_once()

    def test_spoiler(self):
        self.assertFalse(self.race.spoiler)
        self.loop.run_until_complete(self.discord_bot.spoiler(self.discord_bot, ctx=self.context, race_id=self.race_id))
        self.assertTrue(self.race.spoiler)

    def test_ignore(self):
        self.assertFalse(self.race.runners.get('yujito').ignored)
        self.loop.run_until_complete(self.discord_bot.ignore(self.discord_bot, ctx=self.context, race_id=self.race_id, user='yujito'))
        self.assertTrue(self.race.runners.get('yujito').ignored)

    def test_unignore(self):
        self.race.runners.get('yujito').ignored = True
        self.loop.run_until_complete(self.discord_bot.unignore(self.discord_bot, ctx=self.context, race_id=self.race_id, user='yujito'))
        self.assertFalse(self.race.runners.get('yujito').ignored)

    def test_stop_watching(self):
        pass

    def test_finish_race(self):
        self.assertFalse(self.race.runners.get('yujito').finished)
        self.assertFalse(self.race.runners.get('abdalain').finished)
        self.assertFalse(self.race.runners.get('vidgmaddiict').finished)
        self.assertTrue(self.race.runners.get('sidosh').finished)
        self.loop.run_until_complete(self.discord_bot.finish_race(self.discord_bot, self.context, race_id=self.race_id, user='yujito', time='01:51:00.00'))
        self.context.send.assert_called_once_with(f'Finished race for Yujito with time 01:51:00.00 for race {self.race_id}')
        self.assertTrue(self.race.runners.get('yujito').finished)
        race.Race._handle_finish_race.assert_not_called()

        self.loop.run_until_complete(self.discord_bot.finish_race(self.discord_bot, self.context, race_id=self.race_id, user='abdalain', time='01:52:00.00'))
        self.loop.run_until_complete(self.discord_bot.finish_race(self.discord_bot, self.context, race_id=self.race_id, user='sidosh', time='Forfeit'))
        self.loop.run_until_complete(self.discord_bot.finish_race(self.discord_bot, self.context, race_id=self.race_id, user='vidgmaddiict', time='01:53:00.00'))

        self.assertTrue(self.race.runners.get('abdalain').finished)
        self.assertTrue(self.race.runners.get('vidgmaddiict').finished)
        self.assertTrue(self.race.runners.get('sidosh').forfeit)

        race.Race._handle_finish_race.assert_called_once()

    def test_kill(self):
        pass

    def test_racebot_info(self):
        pass

    def test_blacklist(self):
        self.assertFalse(blacklist.check_user('xd_bot_xd'))
        self.loop.run_until_complete(self.discord_bot.blacklist(self.discord_bot, self.context, user='xd_bot_xd'))
        self.assertTrue(blacklist.check_user('xd_bot_xd'))

    def test_unblacklist(self):
        blacklist.add_user('xd_bot_xd')
        self.assertTrue(blacklist.check_user('xd_bot_xd'))
        self.loop.run_until_complete(self.discord_bot.unblacklist(self.discord_bot, self.context, user='xd_bot_xd'))
        self.assertFalse(blacklist.check_user('xd_bot_xd'))

    def test_silence_race(self):
        self.assertFalse(self.race.silenced)
        self.loop.run_until_complete(self.discord_bot.silence_race(self.discord_bot, self.context, race_id=self.race_id))
        self.assertTrue(self.race.silenced)

    def test_unsilence_race(self):
        self.race.silenced = True
        self.loop.run_until_complete(self.discord_bot.unsilence_race(self.discord_bot, self.context, race_id=self.race_id))
        self.assertFalse(self.race.silenced)

    def test_post_results(self):
        self.loop.run_until_complete(self.discord_bot.post_results(self.discord_bot, self.context, race_id=self.race_id))
        exp_standings = f'Race {self.race_id} results:\n\nN/A. Abdalain: (N/A)\nN/A. Yujito: (N/A)\nN/A. vidgmaddiict: (N/A)\nN/A. Sidosh: (Forfeit) (PC fucking restarted by itself, so I desperately tried to die cause I was so pissed that I became personal. Sry for any insults)'
        self.context.send.assert_called_once_with(exp_standings)

        self.loop.run_until_complete(self.discord_bot.finish_race(self.discord_bot, self.context, race_id=self.race_id, user='yujito', time='01:51:00.00'))
        self.loop.run_until_complete(self.discord_bot.finish_race(self.discord_bot, self.context, race_id=self.race_id, user='abdalain', time='01:52:00.00'))
        self.loop.run_until_complete(self.discord_bot.finish_race(self.discord_bot, self.context, race_id=self.race_id, user='sidosh', time='Forfeit'))
        self.loop.run_until_complete(self.discord_bot.finish_race(self.discord_bot, self.context, race_id=self.race_id, user='vidgmaddiict', time='01:53:00.00'))

        self.loop.run_until_complete(self.discord_bot.post_results(self.discord_bot, self.context, race_id=self.race_id))

        exp_standings = f'Race {self.race_id} results:\n\n1. Yujito: (01:51:00.00)\n2. Abdalain: (01:52:00.00)\n3. vidgmaddiict: (01:53:00.00)\nN/A. Sidosh: (Forfeit) (PC fucking restarted by itself, so I desperately tried to die cause I was so pissed that I became personal. Sry for any insults)'
        self.context.send.assert_called_with(exp_standings)

    def test_check_race_for_user(self):
        self.assertIsNone(self.loop.run_until_complete(self.discord_bot.check_race_for_user('hwangbroxd')))
        self.assertIsNotNone(self.loop.run_until_complete(self.discord_bot.check_race_for_user('yujito')))
        self.assertIsNotNone(self.loop.run_until_complete(self.discord_bot.check_race_for_user('yujitoo')))

    def test_check_race_for_watcher(self):
        self.assertTrue(self.loop.run_until_complete(self.discord_bot.check_race_for_watcher('yujitoo', 'abcdef')))
        self.assertFalse(self.loop.run_until_complete(self.discord_bot.check_race_for_watcher('hwangbroxd', 'abcdef')))

if __name__ == '__main__':
    unittest.main()
