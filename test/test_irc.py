import unittest
from unittest.mock import Mock
import irc
from discord.ext import commands
from runner import RunnerSet
import bot
import race
import asyncio
from srlmodels import SRLRace
import cfg
import message

class TestHandleMessage(unittest.TestCase):
    async def add_time_mock(self, user, time_data):
        pass

    async def finish_race_mock(self, user, time_data):
        pass

    def add_watched_runners_mock(self, watcher, runners):
        return {}

    def get_overall_standings_mock(self):
        return []

    async def basic_send_mock(self, msg):
        pass

    async def send_mock(self, msg, channel):
        pass

    async def check_race_for_user_mock(self, user):
        return self.race

    async def update_race_mock(self):
        pass


    def setUp(self):
        b = commands.Bot(command_prefix='!')
        self.bot = bot.DiscordBot(b)

        self._check_race_for_user = bot.DiscordBot.check_race_for_user
        bot.DiscordBot.check_race_for_user = Mock(auto_spec=True, side_effect=self.check_race_for_user_mock)

        self._add_time = race.Race.add_time
        race.Race.add_time = Mock(auto_spec=True, side_effect=self.add_time_mock)

        self._finish_race_for_user = race.Race.finish_race_for_user
        race.Race.finish_race_for_user = Mock(auto_spec=True, side_effect=self.finish_race_mock)

        self._send = irc.IRC.send
        irc.IRC.send = Mock(auto_spec=True, side_effect=self.send_mock)

        self._basic_send = irc.IRC.basic_send
        irc.IRC.basic_send = Mock(auto_spec=True, side_effect=self.basic_send_mock)

        self._add_watched_runners = RunnerSet.set_watchlist
        RunnerSet.set_watchlist = Mock(auto_spec=True, side_effect=self.add_watched_runners_mock)

        self._get_overall_standings = RunnerSet.overall_standings_list
        RunnerSet.overall_standings_list = Mock(auto_spec=True, side_effect=self.get_overall_standings_mock)

        self._update_race = race.Race.update_race
        race.Race.update_race = Mock(auto_spec=True, side_effect=self.update_race_mock)

        self.loop = asyncio.get_event_loop()
        self.tw_irc = irc.IRC(cfg.TW_HOST, cfg.PORT, cfg.TW_NICK, cfg.TW_PASS, 'dummy_account', False, True, self.bot)
        self.srl_irc = irc.IRC(cfg.SRL_HOST, cfg.PORT, cfg.NICK, cfg.SRL_PASS, 'dummy', True, False, self.bot)

        race_dict = {'id': 'q7bsl', 'game': {'id': 6, 'name': 'Pokémon Red/Blue', 'abbrev': 'pkmnredblue', 'popularity': 382.0, 'popularityrank': 5
            }, 'goal': 'any% glitchless no it', 'time': 1624728151, 'state': 3, 'statetext': 'In Progress', 'filename': '', 'numentrants': 4, 'entrants':
                {'vidgmaddiict': {'displayname': 'vidgmaddiict', 'place': 1, 'time': 6945, 'message': '', 'statetext': 'Finished', 'twitch': 'vidgmaddiict', 'trueskill': '583'
                }, 'Yujito': {'displayname': 'Yujito', 'place': 2, 'time': 6946, 'message': '', 'statetext': 'Finished', 'twitch': 'yujitoo', 'trueskill': '434'
                }, 'Abdalain': {'displayname': 'Abdalain', 'place': 9994, 'time': -3, 'message': '', 'statetext': 'Ready', 'twitch': 'abdalain', 'trueskill': '575'
                }, 'Sidosh': {'displayname': 'Sidosh', 'place': 9998, 'time': -1, 'message': 'PC fucking restarted by itself, so I desperately tried to die cause I was so pissed that I became personal. Sry for any insults', 'statetext': 'Forfeit', 'twitch': 'sidosh', 'trueskill': '511'
                }
            }
        }

        race_data = SRLRace(**race_dict)
        self.race = race.Race(race_data.id, self.bot)
        self.bot.races['q7bsl'] = self.race
        # self.tw_irc.race = race.Race(race_data, self.bot)

        self.irc_start = ':hwangbroxd!hwangbroxd@hwangbroxd.tmi.twitch.tv PRIVMSG #xd_bot_xd '
        self.irc_start2 = ':hwangbroxd!hwangbroxd@hwangbroxd.tmi.twitch.tv PRIVMSG #hwangbroxd '

    def tearDown(self):
        race.Race.add_time.mock_reset()
        race.Race.add_time = self._add_time

        race.Race.finish_race_for_user.mock_reset()
        race.Race.finish_race_for_user = self._finish_race_for_user

        RunnerSet.set_watchlist.mock_reset()
        RunnerSet.set_watchlist = self._add_watched_runners

        RunnerSet.overall_standings_list.mock_reset()
        RunnerSet.overall_standings_list = self._get_overall_standings

        race.Race.update_race.mock_reset()
        race.Race.update_race = self._update_race

        bot.DiscordBot.check_race_for_user.mock_reset()
        bot.DiscordBot.check_race_for_user = self._check_race_for_user


    def test_twitch_join_command(self):
        msg = message.Message(self.irc_start + ':!join hwangbroxd')
        self.assertTrue(msg.is_admin)
        self.assertEqual(msg.command, 'join')

        self.loop.run_until_complete(self.tw_irc.handle_message(msg))
        irc.IRC.basic_send.assert_called_once_with('JOIN #hwangbroxd')
        self.assertTrue('hwangbroxd' in self.tw_irc.channels)

    def test_twitch_leave_command(self):
        msg = message.Message(self.irc_start + ':!part hwangbroxd')
        self.tw_irc.channels.add('hwangbroxd')
        self.loop.run_until_complete(self.tw_irc.handle_message(msg))
        irc.IRC.basic_send.assert_called_once_with('PART #hwangbroxd')
        self.assertTrue('hwangbroxd' not in self.tw_irc.channels)

    def test_twitch_watch_command(self):
        msg = message.Message(self.irc_start2 + ':!watch arayalol')
        self.tw_irc.channels.add('hwangbroxd')
        self.assertEqual(msg.command, 'watch')
        self.assertTrue(msg.channel in self.tw_irc.channels)
        self.loop.run_until_complete(self.tw_irc.handle_message(msg))
        RunnerSet.set_watchlist.assert_called_with('hwangbroxd', 'arayalol')

        msg = message.Message(self.irc_start2 + ':!watch arayalol, franchewbacca')
        self.loop.run_until_complete(self.tw_irc.handle_message(msg))
        RunnerSet.set_watchlist.assert_called_with('hwangbroxd', 'arayalol, franchewbacca')

    def test_twitch_reset_watchlist_command(self):
        pass

    def test_twitch_watchlist_command(self):
        pass

    def test_twitch_standings_command(self):
        self.tw_irc.channels.add('xd_bot_xd')
        msg = message.Message(self.irc_start + ':!standings')
        self.loop.run_until_complete(self.tw_irc.handle_message(msg))
        RunnerSet.overall_standings_list.assert_called_once()

    def test_srl_time_command(self):
        irc_raw_string = ':xd_bot_xd2!xd_bot_xd2@SRL-67B2A0C8.oc.oc.cox.net PRIVMSG #srl-q7bsl-livesplit :!time RealTime "Lance" 1:57:22.20'
        msg = message.Message(irc_raw_string)
        self.loop.run_until_complete(self.srl_irc.handle_message(msg))
        race.Race.add_time.assert_called_once()

    def test_srl_done_command(self):
        irc_raw_string = ':xd_bot_xd2!xd_bot_xd2@SRL-67B2A0C8.oc.oc.cox.net PRIVMSG #srl-q7bsl-livesplit :!done RealTime 1:57:22.20'
        msg = message.Message(irc_raw_string)
        self.loop.run_until_complete(self.srl_irc.handle_message(msg))
        race.Race.finish_race_for_user.assert_called_once()

    def test_srl_join_command(self):
        irc_raw_string = ':xd_bot_xd2!xd_bot_xd2@SRL-67B2A0C8.oc.oc.cox.net JOIN :#srl-q7bsl-livesplit'
        msg = message.Message(irc_raw_string)
        self.loop.run_until_complete(self.srl_irc.handle_message(msg))
        race.Race.update_race.assert_called_once()


if __name__ == '__main__':
    unittest.main()
