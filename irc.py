from message import Message
from timestamp import parse_timestamp
import asyncio
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
file_handler = logging.FileHandler('irc-debug.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(logging.StreamHandler())

class IRC:
    def __init__(self, server, port, nickname, password, channel, listener=False, twitch=False, bot=None):
        self.server = server
        self.port = port
        self.nickname = nickname
        self.password = password
        self.channel = channel
        self.channels = {channel}
        self.is_twitch = twitch
        self.listener = listener
        self.bot = bot
        self.alive = False

    #     # debug
    #     self.listen_loop = asyncio.new_event_loop()

    # # debug
    # def run(self):
    #     asyncio.set_event_loop(self.listen_loop)
    #     self.listen_loop.run_until_complete(self.connect())
    #     try:
    #         self.listen_loop.run_until_complete(self._start())
    #     except KeyboardInterrupt:
    #         self.listen_loop.run_until_complete(self.disconnect('inside class'))

    # # debug
    # async def _start(self):
    #     tasks = []
    #     tasks.append(asyncio.create_task(self.listen()))
    #     await asyncio.gather(*tasks)

    async def connect(self) -> None:
        '''Initializes connection to servers

        Handles initial PING for servers and both twitch and SRL connections
        '''

        self.alive = True
        self.reader, self.writer = await asyncio.open_connection(self.server, self.port)
        if self.is_twitch:
            await self.basic_send(f'PASS {self.password}')
            await self.basic_send(f'NICK {self.nickname}')
        else:
            # SRL
            await self.basic_send(f'PASS {self.password}')
            await self.basic_send(f'NICK {self.nickname}')
            await self.basic_send(f'USER {self.nickname} {self.nickname} {self.nickname} :{self.nickname}')
            logger.debug((await self.reader.readline()).decode())
            logger.debug((await self.reader.readline()).decode())
            ping = (await self.reader.readline()).decode()
            logger.debug(ping)
            if 'PING' in ping:
                await self.basic_send(f'PONG :{ping.split("PING :")[1]}')
            await self.basic_send(f'nickserv identify {self.password}')
        if self.listener:
            for channel in self.channels:
                await self._join(channel)

    async def _join(self, channel) -> None:
        '''Low level joining of an irc channel'''
        self.channels.add(channel)
        await self.basic_send(f'JOIN #{channel}')

    async def _part(self, channel) -> None:
        '''Low level leaving of an irc channel'''
        self.channels.discard(channel)
        await self.basic_send(f'PART #{channel}')

    async def basic_send(self, msg) -> None:
        '''Low level sending a message in IRC, with no channel attached'''
        logger.debug(f'BASIC_SEND: {msg}')
        self.writer.write(f'{msg}\r\n'.encode())
        await self.writer.drain()

    async def send(self, msg, channel) -> None:
        '''Sends a message to a given channel'''
        logger.debug(f'SEND: {msg}')
        self.writer.write(f'PRIVMSG #{channel} :{msg}\r\n'.encode())
        await self.writer.drain()

    async def disconnect(self, killer='') -> None:
        '''Disconnect routine'''
        logger.info(f'Closing IRC {self.channels} from {killer}')
        if not self.is_twitch:
            await self.basic_send('nickserv logout')
        self.writer.close()
        await self.writer.wait_closed()

    async def listen(self) -> None:
        '''Basic loop to listen for IRC messages'''
        while self.alive:
            await asyncio.sleep(0.2)
            try:
                raw_bytes = await self.reader.readline()
            except Exception:
                logger.exception('Failed to read from stream')

            try:
                raw_msg = raw_bytes.decode('utf8')
            except UnicodeDecodeError:
                raw_msg = raw_bytes.decode('cp1252')
            if raw_msg and 'GameTime' not in raw_msg and 'PING' not in raw_msg:
                logger.info(raw_msg)

            if raw_msg.startswith('PING'):
                if self.is_twitch:
                    await self.basic_send('PONG :tmi.twitch.tv')
                else:
                    cookie = raw_msg.split('PING :')[1]
                    await self.basic_send(f'PONG :{cookie}')
            elif 'PRIVMSG' in raw_msg or (not self.is_twitch
                                          and ('JOIN :#srl' in raw_msg or 'PART #' in raw_msg)):
                msg = Message(raw_msg)
                cmd_handled = await self.handle_message(msg)
                if cmd_handled:
                    logger.debug(msg)
        await self.disconnect('sub level')

    async def handle_message(self, msg: Message) -> bool:
        '''Handles parsing and running commands for messages

        Returns True if a command was parsed and performed
        '''
        cmd = True
        # SRL commands
        if not self.is_twitch:
            race_id = msg.channel.split('-')[1]
            if race := self.bot.races.get(race_id, {}):
                if msg.command in {'time', 'done'}:
                    if 'GameTime' in msg.message:
                        return
                    if timestamp := parse_timestamp(msg.message):
                        if msg.command == 'time':
                            await race.add_time(msg.username, timestamp)
                        else:
                            await race.finish_race_for_user(msg.username, timestamp)
                elif msg.command in {'JOIN', 'PART'}:
                    await race.update_race()

        # TW commands
        elif msg.command == 'kill' and msg.is_admin and msg.channel == 'xd_bot_xd':
            self.alive = False
        elif msg.command == 'join' and msg.is_admin:
            await self._join(msg.command_body)
        elif msg.command == 'part' and msg.is_admin:
            await self._part(msg.command_body)
        elif msg.command in {'watch', 'reset_watchlist', 'watchlist', 'standings', 'info', 'multitwitch'}:
            if race := await self.bot.check_race_for_user(msg.channel):
                ret = ''
                if msg.command == 'standings':
                    if msg.channel in self.channels:
                        ret = ' '.join(race.runners.overall_standings_list())
                elif msg.command == 'info':
                    ret = race.user_info
                elif msg.command == 'multitwitch':
                    ret = race.multitwitch_link
                elif msg.channel == msg.username:
                    if msg.command == 'watch':
                        if watched := race.runners.set_watchlist(msg.username, msg.command_body):
                            ret = f'Now watching {", ".join([name for name in watched])}'
                    elif msg.command == 'reset_watchlist':
                        ret = 'Reset subset watch list.'
                        race.runners.reset_watchlist(msg.username)
                    elif msg.command == 'watchlist':
                        ret = 'Currently not watching any users. You can use "!watch <user1>, <user2> (...)" to start watching one or more other users.'
                        if watchlist := race.runners.watchlist(msg.username):
                            ret = f'Currently watching: {", ".join([name for name in watchlist])}'
                if ret:
                    logger.info(f'Detected {msg.command} for channel {msg.channel}')
                    await self.send(ret, msg.channel)
        else:
            cmd = False
        return cmd
