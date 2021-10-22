import unittest
from message import Message

class TestMessage(unittest.TestCase):
    def test_srl_message_basic_parse(self):
        irc_raw_string = ':Trueskill3751!xd_bot_xd2@SRL-67B2A0C8.oc.oc.cox.net PRIVMSG #srl-7r05d :test'
        msg = Message(irc_raw_string)
        self.assertEqual(msg.username, 'trueskill3751')
        self.assertFalse(msg.is_command)
        self.assertEqual(msg.message, 'test')
        self.assertFalse(msg.is_admin)
        self.assertEqual(msg.channel, 'srl-7r05d')

    def test_twitch_message_basic_parse(self):
        tw_raw_string = ':hwangbroxd!hwangbroxd@hwangbroxd.tmi.twitch.tv PRIVMSG #xd_bot_xd :u r lame'
        msg = Message(tw_raw_string)
        self.assertEqual(msg.username, 'hwangbroxd')
        self.assertFalse(msg.is_command)
        self.assertTrue(msg.is_admin)
        self.assertEqual(msg.message, 'u r lame')
        self.assertEqual(msg.channel, 'xd_bot_xd')

    # :LegendEater!LegendEate@SRL-2489CB7C.range31-54.btcentralplus.com JOIN :#srl-ysyv4-livesplit
    def test_srl_join(self):
        irc_raw_string = ':xd_bot_xd3!xd_bot_xd3@SRL-67B2A0C8.oc.oc.cox.net JOIN :#srl-drymr-livesplit'
        msg = Message(irc_raw_string)
        self.assertEqual(msg.username, 'xd_bot_xd3')
        self.assertEqual(msg.command, 'JOIN')
        self.assertEqual(msg.channel, 'srl-drymr-livesplit')

        irc_raw_string = ':LegendEater!LegendEate@SRL-2489CB7C.range31-54.btcentralplus.com JOIN :#srl-ysyv4-livesplit'
        msg = Message(irc_raw_string)
        self.assertEqual(msg.username, 'legendeater')
        self.assertEqual(msg.command, 'JOIN')
        self.assertEqual(msg.channel, 'srl-ysyv4-livesplit')

    def test_srl_part(self):
        irc_raw_string = ':xd_bot_xd2!xd_bot_xd2@SRL-67B2A0C8.oc.oc.cox.net PART #srl-uzb7n-livesplit :Leaving'
        msg = Message(irc_raw_string)
        self.assertEqual(msg.username, 'xd_bot_xd2')
        self.assertEqual(msg.command, 'PART')
        self.assertEqual(msg.channel, 'srl-uzb7n-livesplit')

    def test_twitch_message_command(self):
        tw_raw_string = ':hwangbroxd!hwangbroxd@hwangbroxd.tmi.twitch.tv PRIVMSG #xd_bot_xd :!standings'
        msg = Message(tw_raw_string)
        self.assertTrue(msg.is_command)
        self.assertEqual(msg.command, 'standings')
        self.assertEqual(msg.command_body, '')

    def test_twitch_message_command_watchlist(self):
        tw_raw_string = ':hwangbroxd!hwangbroxd@hwangbroxd.tmi.twitch.tv PRIVMSG #xd_bot_xd :!watch arayalol, hwangbroxd'
        msg = Message(tw_raw_string)
        self.assertTrue(msg.is_command)
        self.assertEqual(msg.command, 'watch')
        self.assertEqual(msg.command_body, 'arayalol, hwangbroxd')

    def test_srl_message_command(self):
        irc_raw_string = ':Trueskill3751!xd_bot_xd2@SRL-67B2A0C8.oc.oc.cox.net PRIVMSG #srl-7r05d :!time RealTime "Lance" 1:57:22.20'
        msg = Message(irc_raw_string)
        self.assertTrue(msg.is_command)
        self.assertEqual(msg.command, 'time')
        self.assertEqual(msg.username, 'trueskill3751')
        self.assertEqual(msg.command_body, 'RealTime "Lance" 1:57:22.20')
        self.assertEqual(msg.channel, 'srl-7r05d')

if __name__ == '__main__':
    unittest.main()
