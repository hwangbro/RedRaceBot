import cfg
from pyparsing import Word, alphas, alphanums, restOfLine

# Parser to grab command keywords from chat messages.
username = Word(alphanums+'_-').setResultsName('username')
irc_garb = Word(alphanums+'_!@.-')
channel =  Word(alphanums+'_-').setResultsName('channel')
cmd = ':!' + Word(alphas).setResultsName('cmd')
msg = restOfLine.setResultsName('msg')

parser = ':' + username + irc_garb + 'PRIVMSG' + '#' + channel + cmd + msg
chat_parser = ':' + username + irc_garb + 'PRIVMSG' + '#' + channel + ':' + msg
irc_join = ':' + username + irc_garb + 'JOIN :#' + channel
irc_leave = ':' + username + irc_garb + 'PART #' + channel + ':Leaving'
irc_quit = ':' + username + irc_garb + 'QUIT :Read error'

# :psymar!psymar@SRL-5C0AA961.triad.res.rr.com QUIT :Read error

class Message:
    '''Represents a chat message.

    Has methods to parse internally for different types of
    commands and to assign variables accordingly.
    '''

    def __init__(self, text):
        self.username = self.message = self.command = self.metacommand = self.command_body = self.points_user = self.channel = ''
        self.is_command = False
        self.is_admin = False

        self.admins = cfg.ADMIN

        self.parse_msg(text)
        self.parse_cmd(text)
        self.parse_irc_join(text)
        self.parse_irc_leave(text)

        self.is_admin = self.username in self.admins

    def parse_cmd(self, text) -> None:
        parsed = list(parser.scanString(text))
        if parsed:
            res = parsed[0][0]
            self.channel = res.channel.lower()
            self.command = res.cmd.strip().lower()
            self.command_body = res.msg.strip()
            self.is_command = self.command != ''
            self.is_admin = self.username in self.admins

    def parse_msg(self, text) -> None:
        parsed = list(chat_parser.scanString(text))
        if parsed:
            res = parsed[0][0]
            self.channel = res.channel.lower()
            self.username = res.username.strip().lower()
            self.message = res.msg.strip()

    def parse_irc_join(self, text) -> None:
        parsed = list(irc_join.scanString(text))
        if parsed:
            res = parsed[0][0]
            self.channel = res.channel.strip().lower()
            self.command = 'JOIN'
            self.command_body = self.channel
            self.is_command = True
            self.username = res.username.strip().lower()

    def parse_irc_leave(self, text) -> None:
        parsed = list(irc_leave.scanString(text))
        if parsed:
            res = parsed[0][0]
            self.channel = res.channel.strip().lower()
            self.command = 'PART'
            self.command_body = self.channel
            self.is_command = True
            self.username = res.username.strip().lower()

    def __repr__(self):
        return f'({self.channel}) [{self.username}]: {self.message}'
