import unittest
from unittest.mock import Mock
import asyncio

import irc
from srlmodels import SRLRace
from timestamp import SkipTimestamp, parse_timestamp
from race import Race
import race_db
import blacklist

from discord.ext import commands
import bot
import cfg

class TestRace(unittest.TestCase):
    async def update_mock(self):
        pass

    async def send_mock(self, msg, channel):
        print(f'MSG: {msg}, CHANNEL: {channel}')
        pass

    async def basic_send_mock(self, msg):
        pass

    def setUp(self):
        self._irc_send = irc.IRC.send
        irc.IRC.send = Mock(auto_spec=True, side_effect=self.send_mock)

        self._irc_basic_send = irc.IRC.basic_send
        irc.IRC.basic_send = Mock(auto_spec=True, side_effect=self.basic_send_mock)

        self._update_race = Race.update_race
        Race.update_race = Mock(auto_spec=True, side_effect=self.update_mock)

        race_dict = {'id': 'q7bsl', 'game': {'id': 6, 'name': 'Pokémon Red/Blue', 'abbrev': 'pkmnredblue', 'popularity': 382.0, 'popularityrank': 5
            }, 'goal': 'any% glitchless no it', 'time': 1624728151, 'state': 3, 'statetext': 'In Progress', 'filename': '', 'numentrants': 4, 'entrants':
                {'vidgmaddiict': {'displayname': 'vidgmaddiict', 'place': 1, 'time': 6945, 'message': '', 'statetext': 'Finished', 'twitch': 'vidgmaddiict', 'trueskill': '583'
                }, 'Yujito': {'displayname': 'Yujito', 'place': 2, 'time': 6946, 'message': '', 'statetext': 'Finished', 'twitch': 'yujitoo', 'trueskill': '434'
                }, 'Abdalain': {'displayname': 'Abdalain', 'place': 9994, 'time': -3, 'message': '', 'statetext': 'Ready', 'twitch': 'abdalain', 'trueskill': '575'
                }, 'Sidosh': {'displayname': 'Sidosh', 'place': 9998, 'time': -1, 'message': 'PC fucking restarted by itself, so I desperately tried to die cause I was so pissed that I became personal. Sry for any insults', 'statetext': 'Forfeit', 'twitch': 'sidosh', 'trueskill': '511'
                }
            }
        }

        b = commands.Bot(command_prefix='!')
        self.bot = bot.DiscordBot(b)
        self.bot.srl_irc = irc.IRC(cfg.SRL_HOST, cfg.PORT, cfg.NICK, cfg.SRL_PASS, 'speedrunslive', True, False, bot=self.bot)
        race_data = SRLRace(**race_dict)
        self.race_obj = Race(race_data.id, self.bot)

        self.loop = asyncio.get_event_loop()

        self.loop.run_until_complete(self.race_obj._update_runners(race_data.entrants))

        self.race_obj.runners.get('sidosh').update_status('Ready')
        self.race_obj.runners.get('yujito').update_status('Ready')
        self.race_obj.runners.get('abdalain').update_status('Ready')
        self.race_obj.runners.get('vidgmaddiict').update_status('Ready')

        self.race_obj.twitch_irc_watchers = {'sidosh', 'abdalain', 'yujitoo', 'vidgmaddiict'}

        self.nido_split_1 = parse_timestamp('RealTime "Nido" 7:03.24')
        self.nido_split_2 = parse_timestamp('RealTime "Nido" 7:10.30')
        self.nido_split_3 = parse_timestamp('RealTime "Nidoran" 7:15.38')
        self.nido_split_4 = parse_timestamp('RealTime "Nidoran" 7:20.01')
        self.nido_split_skip = parse_timestamp('RealTime "Nidoran" -')


        self.done_split_1 = parse_timestamp('RealTime 01:52:51.24')
        self.done_split_2 = parse_timestamp('RealTime 01:53:00.30')
        self.done_split_3 = parse_timestamp('RealTime 01:54:30.21')
        self.done_split_4 = parse_timestamp('RealTime 01:55:49.00')

        self.nido_split = self.race_obj.tracked_splits['Nido']

    def tearDown(self):
        irc.IRC.send.mock_reset()
        irc.IRC.send = self._irc_send

        irc.IRC.basic_send.mock_reset()
        irc.IRC.basic_send = self._irc_basic_send

        Race.update_race.mock_reset()
        Race.update_race = self._update_race

    def test_announcing_split(self):
        self.assertEqual(len(self.race_obj.runners), 4)

        nido_split = self.race_obj.tracked_splits['Nido']
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))
        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_2))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_4))

        self.assertTrue(nido_split in self.race_obj.announced_splits)

        runners = self.race_obj.runners
        self.assertEqual(runners.get('sidosh').get_split_time(nido_split).total_ms, 423240)
        self.assertEqual(runners.get('yujito').get_split_time(nido_split).total_ms, 430300)
        self.assertEqual(runners.get('abdalain').get_split_time(nido_split).total_ms, 435380)
        self.assertEqual(runners.get('vidgmaddiict').get_split_time(nido_split).total_ms, 440010)

    # add_time
    def test_skipping_split(self):
        brock_split = self.race_obj.tracked_splits['Brock']

        nido_split_ts = parse_timestamp('RealTime "Nido" 7:03.24')
        brock_split_ts = parse_timestamp('RealTime "Brock" -')

        self.loop.run_until_complete(self.race_obj.add_time('sidosh', nido_split_ts))
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', brock_split_ts))

        self.assertTrue(self.race_obj.runners.get('sidosh').completed_split(brock_split))

    # add_time
    def test_undo_split(self):
        brock_split = self.race_obj.tracked_splits['Brock']

        nido_split_ts = parse_timestamp('RealTime "Nido" 7:03.24')
        brock_split_ts = parse_timestamp('RealTime "Brock" -')

        self.loop.run_until_complete(self.race_obj.add_time('sidosh', nido_split_ts))
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', brock_split_ts))
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', brock_split_ts))

        self.assertFalse(self.race_obj.runners.get('sidosh').completed_split(brock_split), 'Failed to undo skipped split')

    def test_standings(self):
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))
        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_2))

        exp_standings = [
            '1. Sidosh: (Nidoran 07:03.24)',
            '2. Yujito: (Nidoran 07:10.30)',
            '3. Abdalain: (N/A)',
            '4. vidgmaddiict: (N/A)',
        ]
        self.assertEqual(self.race_obj.runners.overall_standings_list(), exp_standings)
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_4))

        exp_standings = [
            '1. Sidosh: (Nidoran 07:03.24)',
            '2. Yujito: (Nidoran 07:10.30)',
            '3. Abdalain: (Nidoran 07:15.38)',
            '4. vidgmaddiict: (Nidoran 07:20.01)'
        ]
        self.assertEqual(self.race_obj.runners.overall_standings_list(), exp_standings)

    def test_standings_with_forfeit(self):
        self.race_obj.runners.get('sidosh').update_status('Forfeit')
        split, ts = self.race_obj.runners.get('sidosh').latest_split
        self.assertEqual(str(split), 'Forfeit - Position: -1')
        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_2))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_4))

        exp_standings = [
            '1. Yujito: (Nidoran 07:10.30)',
            '2. Abdalain: (Nidoran 07:15.38)',
            '3. vidgmaddiict: (Nidoran 07:20.01)',
            'N/A. Sidosh: (Forfeit)'
        ]

        self.assertEqual(self.race_obj.runners.overall_standings_list(), exp_standings)
        self.assertTrue(self.race_obj.tracked_splits['Nido'] in self.race_obj.announced_splits)

        self.race_obj.runners.get('abdalain').update_status('Forfeit')
        exp_standings = [
            '1. Yujito: (Nidoran 07:10.30)',
            '2. vidgmaddiict: (Nidoran 07:20.01)',
            'N/A. Abdalain: (Forfeit)',
            'N/A. Sidosh: (Forfeit)'
        ]
        self.assertEqual(self.race_obj.runners.overall_standings_list(), exp_standings)
        self.loop.run_until_complete(self.race_obj.add_time('yujito', parse_timestamp('RealTime "Brock" 11:58.29')))

        exp_standings = [
            '1. Yujito: (Brock 11:58.29)',
            '2. vidgmaddiict: (Nidoran 07:20.01)',
            'N/A. Abdalain: (Forfeit)',
            'N/A. Sidosh: (Forfeit)'
        ]
        self.assertEqual(self.race_obj.runners.overall_standings_list(), exp_standings)

    def test_standings_with_skipped_and_ff(self):
        self.race_obj.runners.get('sidosh').update_status('Forfeit')
        split, ts = self.race_obj.runners.get('sidosh').latest_split
        self.assertEqual(str(split), 'Forfeit - Position: -1')
        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_2))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_skip))
        self.assertTrue(isinstance(self.nido_split_skip, SkipTimestamp))
        split, ts = self.race_obj.runners.get('vidgmaddiict').latest_split

        exp_standings = [
            '1. Yujito: (Nidoran 07:10.30)',
            '2. Abdalain: (Nidoran 07:15.38)',
            '3. vidgmaddiict: (N/A)',
            'N/A. Sidosh: (Forfeit)'
        ]

        self.assertEqual(self.race_obj.runners.overall_standings_list(), exp_standings)
        self.assertTrue(self.race_obj.tracked_splits['Nido'] in self.race_obj.announced_splits)

    def test_standings_with_ignored_runner(self):
        self.race_obj.runners.get('sidosh').ignored = True
        split, ts = self.race_obj.runners.get('sidosh').latest_split
        self.assertEqual(str(split), 'N/A - Position: 0')
        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_2))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_4))

        exp_standings = [
            '1. Yujito: (Nidoran 07:10.30)',
            '2. Abdalain: (Nidoran 07:15.38)',
            '3. vidgmaddiict: (Nidoran 07:20.01)',
            '4. Sidosh: (N/A)'
        ]

        self.assertEqual(self.race_obj.runners.overall_standings_list(), exp_standings)
        self.assertTrue(self.race_obj.tracked_splits['Nido'] in self.race_obj.announced_splits)

    def test_standings_with_ignored_and_skipped(self):
        self.race_obj.runners.get('sidosh').ignored = True

        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_2))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', parse_timestamp('RealTime "Rival 1" 3:03.24')))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_skip))

        exp_standings = [
            '1. Yujito: (Nidoran 07:10.30)',
            '2. Abdalain: (Nidoran 07:15.38)',
            '3. vidgmaddiict: (Rival 1 03:03.24)',
            '4. Sidosh: (N/A)'
        ]

        self.assertEqual(self.race_obj.runners.overall_standings_list(), exp_standings)
        self.assertTrue(self.race_obj.tracked_splits['Nido'] in self.race_obj.announced_splits)

    def test_standings_with_ignored_and_ff(self):
        self.race_obj.runners.get('vidgmaddiict').ignored = True
        self.race_obj.runners.get('sidosh').update_status('Forfeit')
        split, ts = self.race_obj.runners.get('sidosh').latest_split
        self.assertEqual(str(split), 'Forfeit - Position: -1')
        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_2))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))

        exp_standings = [
            '1. Yujito: (Nidoran 07:10.30)',
            '2. Abdalain: (Nidoran 07:15.38)',
            '3. vidgmaddiict: (N/A)',
            'N/A. Sidosh: (Forfeit)'
        ]

        self.assertEqual(self.race_obj.runners.overall_standings_list(), exp_standings)
        self.assertTrue(self.race_obj.tracked_splits['Nido'] in self.race_obj.announced_splits)

    def test_standings_with_ignored_and_skipped_and_ff(self):
        self.race_obj.runners.get('vidgmaddiict').ignored = True
        self.race_obj.runners.get('sidosh').update_status('Forfeit')
        split, ts = self.race_obj.runners.get('sidosh').latest_split
        self.assertEqual(str(split), 'Forfeit - Position: -1')
        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_2))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_skip))

        exp_standings = [
            '1. Yujito: (Nidoran 07:10.30)',
            '2. Abdalain: (N/A)',
            '3. vidgmaddiict: (N/A)',
            'N/A. Sidosh: (Forfeit)'
        ]

        self.assertEqual(self.race_obj.runners.overall_standings_list(), exp_standings)
        self.assertTrue(self.race_obj.tracked_splits['Nido'] in self.race_obj.announced_splits)

    def test_standings_finished(self):
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('sidosh', self.done_split_1))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('yujito', self.done_split_2))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('abdalain', self.done_split_3))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('vidgmaddiict', self.done_split_4))

        exp_standings = [
            '1. Sidosh: (01:52:51.24)',
            '2. Yujito: (01:53:00.30)',
            '3. Abdalain: (01:54:30.21)',
            '4. vidgmaddiict: (01:55:49.00)'
        ]
        self.assertEqual(self.race_obj.runners.overall_standings_list(True), exp_standings)

    def test_standings_finished_with_unfinished_racer(self):
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('sidosh', self.done_split_1))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('yujito', self.done_split_2))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('abdalain', self.done_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_4))

        exp_standings = [
            '1. Sidosh: (01:52:51.24)',
            '2. Yujito: (01:53:00.30)',
            '3. Abdalain: (01:54:30.21)',
            'N/A. vidgmaddiict: (N/A)'
        ]

        self.assertEqual(self.race_obj.runners.overall_standings_list(True), exp_standings)

    def test_standings_finished_with_forfeit(self):
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('sidosh', self.done_split_1))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('yujito', self.done_split_2))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('abdalain', self.done_split_3))
        self.race_obj.runners.get('vidgmaddiict').update_status('Forfeit')

        exp_standings = [
            '1. Sidosh: (01:52:51.24)',
            '2. Yujito: (01:53:00.30)',
            '3. Abdalain: (01:54:30.21)',
            'N/A. vidgmaddiict: (Forfeit)'
        ]

        self.assertEqual(self.race_obj.runners.overall_standings_list(True), exp_standings)

    def test_watched_runners(self):
        x = self.race_obj.runners.set_watchlist('sidosh', 'abdalain')
        self.assertEqual(x, {'abdalain'})

        x = self.race_obj.runners.set_watchlist('abdalain', 'sidosh, yujitoo')
        self.assertEqual(x, {'sidosh', 'yujitoo'})

        x = self.race_obj.runners.set_watchlist('abdalain', 'sidosh, yujito')
        self.assertEqual(x, {'sidosh', 'yujitoo'})

    def test_subset_announce(self):
        self.race_obj.runners.set_watchlist('sidosh', 'abdalain')

        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))
        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_2))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))

        self.assertEqual(irc.IRC.send.call_count, 1)
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_4))

        self.assertTrue(self.nido_split in self.race_obj.announced_splits)
        self.assertEqual(irc.IRC.send.call_count, 5)

    def test_subset_announce_2(self):
        self.race_obj.runners.set_watchlist('sidosh', 'abdalain')
        self.race_obj.runners.set_watchlist('abdalain', 'yujitoo, vidgmaddiict')

        self.assertEqual(self.race_obj.runners.get('sidosh').watched_runners, {'abdalain'})
        self.assertEqual(self.race_obj.runners.get('abdalain').watched_runners, {'yujitoo', 'vidgmaddiict'})

        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))
        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_2))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))

        self.assertEqual(irc.IRC.send.call_count, 1)
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_4))

        self.assertTrue(self.nido_split in self.race_obj.announced_splits)
        self.assertEqual(irc.IRC.send.call_count, 6)

    def test_get_split_standings(self):
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))
        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_2))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_4))

        self.assertEqual(irc.IRC.send.call_count, 4)

        announcement = self.race_obj.runners.split_standings(self.nido_split, self.race_obj.runners)
        # announcement2 = self.loop.run_until_complete(self.race_obj.get_split_standings2(self.nido_split, self.race_obj.runners))
        self.assertEqual(announcement, 'Nidoran split standings: 1. Sidosh - 07:03.24. 2. Yujito - 07:10.30. 3. Abdalain - 07:15.38. 4. vidgmaddiict - 07:20.01.')

        # self.assertEqual(announcement, announcement2)

    def test_get_split_standings_with_ff(self):
        self.race_obj.runners.get('yujito').update_status('Forfeit')
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_4))

        self.assertEqual(irc.IRC.send.call_count, 4)

        announcement = self.race_obj.runners.split_standings(self.nido_split, self.race_obj.runners)
        self.assertEqual(announcement, 'Nidoran split standings: 1. Sidosh - 07:03.24. 2. Abdalain - 07:15.38. 3. vidgmaddiict - 07:20.01. N/A. Yujito - Forfeit.')


    def test_get_split_standings_with_skips(self):
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_4))
        self.loop.run_until_complete(self.race_obj.add_time('yujito', self.nido_split_skip))

        self.assertEqual(irc.IRC.send.call_count, 4)

        announcement = self.race_obj.runners.split_standings(self.nido_split, self.race_obj.runners)
        self.assertEqual(announcement, 'Nidoran split standings: 1. Sidosh - 07:03.24. 2. Abdalain - 07:15.38. 3. vidgmaddiict - 07:20.01. 4. Yujito - Skipped.')


    def test_get_split_standings_with_skips_and_ff(self):
        self.race_obj.runners.get('yujito').update_status('Forfeit')
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_skip))

        self.assertEqual(irc.IRC.send.call_count, 4)
        announcement = self.race_obj.runners.split_standings(self.nido_split, self.race_obj.runners)

        self.assertEqual(announcement, 'Nidoran split standings: 1. Sidosh - 07:03.24. 2. Abdalain - 07:15.38. 3. vidgmaddiict - Skipped. N/A. Yujito - Forfeit.')

    def test_get_split_standings_with_ignored(self):
        self.race_obj.runners.get('yujito').ignored = True
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_4))

        self.assertEqual(irc.IRC.send.call_count, 4)

        announcement = self.race_obj.runners.split_standings(self.nido_split, self.race_obj.runners)

        self.assertEqual(announcement, 'Nidoran split standings: 1. Sidosh - 07:03.24. 2. Abdalain - 07:15.38. 3. vidgmaddiict - 07:20.01. 4. Yujito - N/A.')

    def test_get_split_standings_with_ignored_and_skip(self):
        self.race_obj.runners.get('yujito').ignored = True
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))
        self.loop.run_until_complete(self.race_obj.add_time('abdalain', self.nido_split_3))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_skip))

        self.assertEqual(irc.IRC.send.call_count, 4)

        announcement = self.race_obj.runners.split_standings(self.nido_split, self.race_obj.runners)
        self.assertEqual(announcement, 'Nidoran split standings: 1. Sidosh - 07:03.24. 2. Abdalain - 07:15.38. 3. vidgmaddiict - Skipped. 4. Yujito - N/A.')

    def test_get_split_standings_with_ignored_and_ff(self):
        self.race_obj.runners.get('yujito').ignored = True
        self.race_obj.runners.get('vidgmaddiict').update_status('Forfeit')
        self.race_obj.runners.get('abdalain').update_status('Forfeit')
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))

        self.assertEqual(irc.IRC.send.call_count, 4)

        announcement = self.race_obj.runners.split_standings(self.nido_split, self.race_obj.runners)
        self.assertEqual(announcement, 'Nidoran split standings: 1. Sidosh - 07:03.24. 2. Yujito - N/A. N/A. Abdalain - Forfeit. N/A. vidgmaddiict - Forfeit.')

    def test_get_split_standings_with_ignored_and_skip_and_ff(self):
        self.race_obj.runners.get('yujito').ignored = True
        self.race_obj.runners.get('abdalain').update_status('Forfeit')
        self.loop.run_until_complete(self.race_obj.add_time('sidosh', self.nido_split_1))
        self.loop.run_until_complete(self.race_obj.add_time('vidgmaddiict', self.nido_split_skip))

        self.assertEqual(irc.IRC.send.call_count, 4)

        announcement = self.race_obj.runners.split_standings(self.nido_split, self.race_obj.runners)
        self.assertEqual(announcement, 'Nidoran split standings: 1. Sidosh - 07:03.24. 2. vidgmaddiict - Skipped. 3. Yujito - N/A. N/A. Abdalain - Forfeit.')


class TestFinishingRace(unittest.TestCase):
    async def basic_send_mock(self, msg):
        pass

    async def send_mock(self, msg, channel):
        pass

    async def part_mock(self, channel):
        pass

    async def send_message_mock(self, msg, channel):
        pass

    async def sleep_mock(self, sec):
        pass

    async def async_mock(self, *args):
        pass

    def setUp(self):
        self._send = irc.IRC.send
        irc.IRC.send = Mock(auto_spec=True, side_effect=self.send_mock)

        self._basic_send = irc.IRC.basic_send
        irc.IRC.basic_send = Mock(auto_spec=True, side_effect=self.basic_send_mock)

        self._part = irc.IRC._part
        irc.IRC._part = Mock(auto_spec=True, side_effect=self.part_mock)

        self._update_race_db = race_db.update_race
        race_db.update_race = Mock(auto_spec=True)

        self._update_race_comments = Race.update_race_comments
        Race.update_race_comments = Mock(auto_spec=True, side_effect=self.async_mock)

        self._send_message = bot.DiscordBot.send_message
        bot.DiscordBot.send_message = Mock(auto_spec=True, side_effect=self.send_message_mock)

        b = commands.Bot(command_prefix='!')
        self.discord_bot = bot.DiscordBot(b)
        self.discord_bot.srl_irc = irc.IRC(cfg.SRL_HOST, cfg.PORT, cfg.NICK, cfg.SRL_PASS, 'speedrunslive', True, False, bot=self.discord_bot)

        race_dict = {'id': 'q7bsl', 'game': {'id': 6, 'name': 'Pokémon Red/Blue', 'abbrev': 'pkmnredblue', 'popularity': 382.0, 'popularityrank': 5
            }, 'goal': 'any% glitchless no it', 'time': 1624728151, 'state': 3, 'statetext': 'In Progress', 'filename': '', 'numentrants': 4, 'entrants':
                {'vidgmaddiict': {'displayname': 'vidgmaddiict', 'place': 1, 'time': 6945, 'message': '', 'statetext': 'Finished', 'twitch': 'vidgmaddiict', 'trueskill': '583'
                }, 'Yujito': {'displayname': 'Yujito', 'place': 2, 'time': 6946, 'message': '', 'statetext': 'Finished', 'twitch': 'yujitoo', 'trueskill': '434'
                }, 'Abdalain': {'displayname': 'Abdalain', 'place': 9994, 'time': -3, 'message': '', 'statetext': 'Ready', 'twitch': 'abdalain', 'trueskill': '575'
                }, 'Sidosh': {'displayname': 'Sidosh', 'place': 9998, 'time': -1, 'message': '', 'statetext': 'Forfeit', 'twitch': 'sidosh', 'trueskill': '511'
                }
            }
        }

        self.race_dict_ff = {'id': 'q7bsl', 'game': {'id': 6, 'name': 'Pokémon Red/Blue', 'abbrev': 'pkmnredblue', 'popularity': 382.0, 'popularityrank': 5
            }, 'goal': 'any% glitchless no it', 'time': 1624728151, 'state': 3, 'statetext': 'In Progress', 'filename': '', 'numentrants': 4, 'entrants':
                {'vidgmaddiict': {'displayname': 'vidgmaddiict', 'place': 1, 'time': 6945, 'message': '', 'statetext': 'Forfeit', 'twitch': 'vidgmaddiict', 'trueskill': '583'
                }, 'Yujito': {'displayname': 'Yujito', 'place': 2, 'time': 6946, 'message': '', 'statetext': 'Finished', 'twitch': 'yujitoo', 'trueskill': '434'
                }, 'Abdalain': {'displayname': 'Abdalain', 'place': 9994, 'time': -3, 'message': '', 'statetext': 'Forfeit', 'twitch': 'abdalain', 'trueskill': '575'
                }, 'Sidosh': {'displayname': 'Sidosh', 'place': 9998, 'time': -1, 'message': '', 'statetext': 'Ready', 'twitch': 'sidosh', 'trueskill': '511'
                }
            }
        }
        race_data = SRLRace(**race_dict)
        self.race_obj = Race(race_data.id, self.discord_bot)

        self._sleep = asyncio.sleep
        asyncio.sleep = Mock(auto_spec=True, side_effect=self.sleep_mock)

        self.loop = asyncio.get_event_loop()

        self.loop.run_until_complete(self.race_obj._update_runners(race_data.entrants))

        self.race_obj.runners.get('sidosh').update_status('Ready')
        self.race_obj.runners.get('yujito').update_status('Ready')
        self.race_obj.runners.get('abdalain').update_status('Ready')
        self.race_obj.runners.get('vidgmaddiict').update_status('Ready')
        self.race_obj.twitch_irc_watchers = {'sidosh', 'abdalain', 'yujitoo', 'vidgmaddiict'}

        self.nido_split_1 = parse_timestamp('RealTime "Nido" 7:03.24')
        self.nido_split_2 = parse_timestamp('RealTime "Nido" 7:10.30')
        self.nido_split_3 = parse_timestamp('RealTime "Nidoran" 7:15.38')
        self.nido_split_4 = parse_timestamp('RealTime "Nidoran" 7:20.01')

        self.done_split = self.race_obj.tracked_splits['Done']

    def tearDown(self):
        irc.IRC.send.reset_mock()
        irc.IRC.send = self._send

        irc.IRC.basic_send.reset_mock()
        irc.IRC.basic_send = self._basic_send

        irc.IRC._part.reset_mock()
        irc.IRC._part = self._part

        race_db.update_race.reset_mock()
        race_db.update_race = self._update_race_db

        bot.DiscordBot.send_message.reset_mock()
        bot.DiscordBot.send_message = self._send_message

        Race.update_race_comments.reset_mock()
        Race.update_race_comments = self._update_race_comments

        asyncio.sleep.reset_mock()
        asyncio.sleep = self._sleep

    def test_finishing_race(self):
        self.done_split_1 = parse_timestamp('RealTime 01:50:03.24')
        self.done_split_2 = parse_timestamp('RealTime 01:51:10.30')
        self.done_split_3 = parse_timestamp('RealTime 01:52:15.38')
        self.done_split_4 = parse_timestamp('RealTime 01:53:20.01')

        self.assertFalse(self.race_obj.runners.split_is_complete(self.done_split))

        self.loop.run_until_complete(self.race_obj.finish_race_for_user('sidosh', self.done_split_1))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('abdalain', self.done_split_2))

        self.assertFalse(self.race_obj.runners.split_is_complete(self.done_split))

        self.loop.run_until_complete(self.race_obj.finish_race_for_user('yujito', self.done_split_3))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('vidgmaddiict', self.done_split_4))

        self.assertTrue(self.race_obj.runners.split_is_complete(self.done_split))

        self.assertEqual(irc.IRC.send.call_count, 4)
        race_db.update_race.assert_called_once_with('q7bsl', True)
        self.assertEqual(irc.IRC._part.call_count, 5)
        self.assertEqual(bot.DiscordBot.send_message.call_count, 2)
        self.assertEqual(asyncio.sleep.call_count, 2)

        exp_standings = [
            '1. Sidosh: (01:50:03.24)',
            '2. Abdalain: (01:51:10.30)',
            '3. Yujito: (01:52:15.38)',
            '4. vidgmaddiict: (01:53:20.01)'
        ]
        self.assertEqual(exp_standings, self.race_obj.runners.overall_standings_list(True))

    def test_finishing_race_with_ff(self):
        self.done_split_1 = parse_timestamp('RealTime 01:50:03.24')
        self.done_split_2 = parse_timestamp('RealTime 01:51:10.30')
        self.race_obj.runners.get('abdalain').update_status('Forfeit')
        self.race_obj.runners.get('vidgmaddiict').update_status('Forfeit')

        self.assertFalse(self.race_obj.runners.split_is_complete(self.done_split))

        self.loop.run_until_complete(self.race_obj.finish_race_for_user('sidosh', self.done_split_1))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('yujito', self.done_split_2))

        self.assertTrue(self.race_obj.runners.split_is_complete(self.done_split))

        self.assertEqual(irc.IRC.send.call_count, 4)
        race_db.update_race.assert_called_once_with('q7bsl', True)

        self.assertEqual(irc.IRC._part.call_count, 5)
        self.assertEqual(bot.DiscordBot.send_message.call_count, 2)

        exp_standings = [
            '1. Sidosh: (01:50:03.24)',
            '2. Yujito: (01:51:10.30)',
            'N/A. Abdalain: (Forfeit)',
            'N/A. vidgmaddiict: (Forfeit)',
        ]
        self.assertEqual(exp_standings, self.race_obj.runners.overall_standings_list(True))

    def test_finishing_race_with_last_ff(self):
        self.done_split_1 = parse_timestamp('RealTime 01:50:03.24')
        self.done_split_2 = parse_timestamp('RealTime 01:51:10.30')
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('sidosh', self.done_split_1))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('yujito', self.done_split_2))
        irc.IRC.send.assert_not_called()
        self.assertFalse(self.race_obj.runners.split_is_complete(self.done_split))
        race_data = SRLRace(**self.race_dict_ff)
        announce = self.loop.run_until_complete(self.race_obj._update_runners(race_data.entrants))
        self.assertTrue(announce)
        self.loop.run_until_complete(self.race_obj._check_all_splits_announcement())
        self.assertTrue(self.race_obj.runners.split_is_complete(self.done_split))
        self.assertEqual(irc.IRC.send.call_count, 2)

    def test_standings_with_spoiler(self):
        self.done_split_1 = parse_timestamp('RealTime 01:50:03.24')
        self.done_split_2 = parse_timestamp('RealTime 01:51:10.30')
        self.race_obj.runners.get('abdalain').update_status('Forfeit')
        self.race_obj.runners.get('vidgmaddiict').update_status('Forfeit')

        self.assertFalse(self.race_obj.runners.split_is_complete(self.done_split))

        self.loop.run_until_complete(self.race_obj.finish_race_for_user('sidosh', self.done_split_1))
        self.loop.run_until_complete(self.race_obj.finish_race_for_user('yujito', self.done_split_2))

        self.assertTrue(self.race_obj.runners.split_is_complete(self.done_split))

        self.assertEqual(irc.IRC.send.call_count, 4)
        race_db.update_race.assert_called_once_with('q7bsl', True)

        self.assertEqual(irc.IRC._part.call_count, 5)
        self.assertEqual(bot.DiscordBot.send_message.call_count, 2)

        exp_str = '||1. Sidosh: (01:50:03.24)\n2. Yujito: (01:51:10.30)\nN/A. Abdalain: (Forfeit)\nN/A. vidgmaddiict: (Forfeit)||'
        self.assertEqual(exp_str, self.race_obj.runners.standings(True))

class TestAddRunners(unittest.TestCase):
    async def join_mock(self, channel):
        pass

    async def part_mock(self, channel):
        pass

    def setUp(self):
        race_dict = {'id': 'q7bsl', 'game': {'id': 6, 'name': 'Pokémon Red/Blue', 'abbrev': 'pkmnredblue', 'popularity': 382.0, 'popularityrank': 5
            }, 'goal': 'any% glitchless no it', 'time': 1624728151, 'state': 3, 'statetext': 'In Progress', 'filename': '', 'numentrants': 4, 'entrants':
                {'vidgmaddiict': {'displayname': 'vidgmaddiict', 'place': 1, 'time': 6945, 'message': '', 'statetext': 'Finished', 'twitch': 'vidgmaddiict', 'trueskill': '583'
                }, 'Yujito': {'displayname': 'Yujito', 'place': 2, 'time': 6946, 'message': '', 'statetext': 'Finished', 'twitch': 'yujitoo', 'trueskill': '434'
                }, 'Abdalain': {'displayname': 'Abdalain', 'place': 9994, 'time': -3, 'message': '', 'statetext': 'Ready', 'twitch': 'abdalain', 'trueskill': '575'
                }, 'Sidosh': {'displayname': 'Sidosh', 'place': 9998, 'time': -1, 'message': 'PC fucking restarted by itself, so I desperately tried to die cause I was so pissed that I became personal. Sry for any insults', 'statetext': 'Forfeit', 'twitch': 'sidosh', 'trueskill': '511'
                }
            }
        }

        b = commands.Bot(command_prefix='!')
        self.bot = bot.DiscordBot(b)
        self.bot.twitch_irc = irc.IRC(cfg.TW_HOST, cfg.PORT, cfg.NICK, cfg.TW_HOST, 'dummy', True, True, bot=self.bot)
        self.race_data = SRLRace(**race_dict)
        self.race_obj = Race(self.race_data.id, self.bot)

        self.loop = asyncio.get_event_loop()

        self._join = irc.IRC._join
        irc.IRC._join = Mock(auto_spec=True, side_effect=self.join_mock)
        self._part = irc.IRC._part
        irc.IRC._part = Mock(auto_spec=True, side_effect=self.part_mock)

    def tearDown(self):
        irc.IRC._join.reset_mock()
        irc.IRC._join = self._join
        irc.IRC._part.reset_mock()
        irc.IRC._part = self._part

    def test_adding_one_runner(self):
        self.loop.run_until_complete(self.race_obj._update_runners(self.race_data.entrants))
        self.assertEqual(len(self.race_obj.runners), 4)
        self.assertEqual(len(self.race_obj.twitch_irc_watchers), 3)

    def test_adding_blacklisted_runners(self):
        blacklist.add_user('yujitoo')
        self.assertTrue(blacklist.check_user('yujitoo'))
        self.loop.run_until_complete(self.race_obj._update_runners(self.race_data.entrants))
        self.assertEqual(len(self.race_obj.runners), 4)
        self.assertEqual(len(self.race_obj.twitch_irc_watchers), 2)
        blacklist.remove_user('yujitoo')

    def test_removing_user_before_race_starts(self):
        race_dict = {'id': 'q7bsl', 'game': {'id': 6, 'name': 'Pokémon Red/Blue', 'abbrev': 'pkmnredblue', 'popularity': 382.0, 'popularityrank': 5
            }, 'goal': 'any% glitchless no it', 'time': 1624728151, 'state': 3, 'statetext': 'In Progress', 'filename': '', 'numentrants': 4, 'entrants':
                {'vidgmaddiict': {'displayname': 'vidgmaddiict', 'place': 1, 'time': 6945, 'message': '', 'statetext': 'Finished', 'twitch': 'vidgmaddiict', 'trueskill': '583'
                }, 'Abdalain': {'displayname': 'Abdalain', 'place': 9994, 'time': -3, 'message': '', 'statetext': 'Ready', 'twitch': 'abdalain', 'trueskill': '575'
                }, 'Sidosh': {'displayname': 'Sidosh', 'place': 9998, 'time': -1, 'message': 'PC fucking restarted by itself, so I desperately tried to die cause I was so pissed that I became personal. Sry for any insults', 'statetext': 'Forfeit', 'twitch': 'sidosh', 'trueskill': '511'
                }
            }
        }
        race_data = SRLRace(**race_dict)
        self.loop.run_until_complete(self.race_obj._update_runners(self.race_data.entrants))
        self.assertEqual(len(self.race_obj.runners), 4)
        self.assertIsNotNone(self.race_obj.runners.get('yujito'))
        self.loop.run_until_complete(self.race_obj._update_runners(race_data.entrants))
        self.assertEqual(len(self.race_obj.runners), 3)
        self.assertIsNone(self.race_obj.runners.get('yujito'))

class TestStringReturns(unittest.TestCase):
    async def _update_irc_watchers_mock(self, *args):
        pass

    def setUp(self) -> None:
        race_dict = {'id': 'q7bsl', 'game': {'id': 6, 'name': 'Pokémon Red/Blue', 'abbrev': 'pkmnredblue', 'popularity': 382.0, 'popularityrank': 5
            }, 'goal': 'any% glitchless no it', 'time': 1624728151, 'state': 3, 'statetext': 'In Progress', 'filename': '', 'numentrants': 4, 'entrants':
                {'vidgmaddiict': {'displayname': 'vidgmaddiict', 'place': 1, 'time': 6945, 'message': '', 'statetext': 'Finished', 'twitch': 'vidgmaddiict', 'trueskill': '583'
                }, 'Yujito': {'displayname': 'Yujito', 'place': 2, 'time': 6946, 'message': '', 'statetext': 'Finished', 'twitch': 'yujitoo', 'trueskill': '434'
                }, 'Abdalain': {'displayname': 'Abdalain', 'place': 9994, 'time': -3, 'message': '', 'statetext': 'Ready', 'twitch': 'abdalain', 'trueskill': '575'
                }, 'Sidosh': {'displayname': 'Sidosh', 'place': 9998, 'time': -1, 'message': '', 'statetext': 'Forfeit', 'twitch': 'sidosh', 'trueskill': '511'
                }
            }
        }

        self.__update_irc_watchers = Race._update_irc_watchers
        Race._update_irc_watchers = Mock(auto_spec=True, side_effect=self._update_irc_watchers_mock)

        b = commands.Bot(command_prefix='!')
        self.bot = bot.DiscordBot(b)
        self.bot.twitch_irc = irc.IRC(cfg.TW_HOST, cfg.PORT, cfg.NICK, cfg.TW_HOST, 'dummy', True, True, bot=self.bot)
        race_data = SRLRace(**race_dict)
        self.race_obj = Race(race_data.id, self.bot)
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.race_obj._update_runners(race_data.entrants))

    def tearDown(self) -> None:
        Race._update_irc_watchers.reset_mock()
        Race._update_irc_watchers = self.__update_irc_watchers

    def test_generate_multitwitch_link(self):
        url = self.race_obj.multitwitch_link
        exp_url = 'https://multitwitch.tv/abdalain/vidgmaddiict/yujitoo/'
        self.assertEqual(url, exp_url, 'Bad multitwitch link')

    def test_generate_user_info(self):
        info = self.race_obj.user_info
        exp_info = 'Runner info | Abdalain - twitch.tv/abdalain | Sidosh - twitch.tv/sidosh | vidgmaddiict - twitch.tv/vidgmaddiict | Yujito - twitch.tv/yujitoo | '
        self.assertEqual(info, exp_info, 'Bad runner info generated')

if __name__ == '__main__':
    unittest.main()
