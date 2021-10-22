import asyncio

import irc
import cfg
import srlapi
from race import Race
import blacklist
import race_db
import timestamp

from discord.ext import commands
from discord import Message

import logging
logger = logging.getLogger('main')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
file_handler = logging.FileHandler('bot.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(logging.StreamHandler())


class DiscordBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.races = {}
        self.srl_irc = None
        self.twitch_irc = irc.IRC(cfg.TW_HOST, cfg.PORT, cfg.TW_NICK, cfg.TW_PASS, 'xd_bot_xd', True, True, bot=self)

    async def is_race_channel(ctx) -> bool:
        test_server = ctx.guild.id == cfg.TEST_DISCORD_SERVER_ID and ctx.channel.name == 'test'
        race_server = ctx.guild.id == cfg.RACE_DISCORD_SERVER_ID and ctx.channel.id == cfg.RACE_BOT_CHANNEL_ID
        return test_server or race_server

    async def is_admin(ctx) -> bool:
        return ctx.author.id == cfg.DISCORD_HWANGBRO_ID

    @commands.command()
    @commands.check(is_race_channel)
    async def watch(self, ctx, user: str, *args) -> None:
        '''Basic command to trigger watching a race'''

        reply_text = f'Searching for race with user {user}'
        reply = await ctx.send(reply_text)
        race_model = srlapi.find_race_with_user(user)
        if race_model and race_model.game.id == 6:
            race_id = race_model.id
            if race_db.check_race(race_id):
                reply_text = f'Already watching {race_id}:\n{race_model.summary_str()}'
            else:
                await self.init_ircs(race_id)

                logger.info(f'Found race {race_model}')
                race_obj = Race(race_id, self)
                race_obj.watch_msg = reply
                self.races[race_id] = race_obj
                race_db.add_race(race_id)
                await race_obj.update_race()
                await asyncio.sleep(2)
                reply_text = f'Found a race! ID: {race_id}\n{race_model.summary_str()}\nThis race will now be tracked'
                if 'silent' in args or 'silence' in args:
                    race_obj.silenced = True
                    reply_text += ' silently'
                if 'spoiler' in args:
                    race_obj.spoiler = True
                    reply_text += ' and marked as a spoiler'
        else:
            reply_text = f'Unable to find a race involving user {user}'

        await reply.edit(content=reply_text)

    async def init_ircs(self, race_id: str) -> None:
        '''Initializes the SRL and TW IRC clients'''
        if not self.srl_irc:
            self.srl_irc = irc.IRC(cfg.SRL_HOST, cfg.PORT, cfg.NICK, cfg.SRL_PASS, f'srl-{race_id}-livesplit', True, False, bot=self)

        for chat in [self.srl_irc, self.twitch_irc]:
            if not chat.alive:
                await chat.connect()
                self.bot.loop.create_task(chat.listen())

            if not chat.is_twitch and f'srl-{race_id}-livesplit' not in chat.channels:
                await chat._join(f'srl-{race_id}-livesplit')

    @commands.command()
    @commands.check(is_race_channel)
    async def add_watcher(self, ctx, race_id: str, watcher: str) -> None:
        '''Adds an external (non-participant) watcher'''

        msg = ''
        if race := self.races.get(race_id, None):
            added = await race.add_external_watcher(watcher)
            if added:
                msg = f'Added {watcher} as a watcher of {race_id}'
        else:
            msg = f'Could not find race {race_id}'

        await ctx.send(msg)

    @commands.command()
    @commands.check(is_admin)
    @commands.check(is_race_channel)
    async def update_race(self, ctx, race_id: str) -> None:
        '''Race.update_race()'''

        msg = f'Could not find race {race_id}'
        if race := self.races.get(race_id, None):
            await race.update_race()
            msg = f'Updating race {race_id}'

        await ctx.send(msg)

    @commands.command()
    @commands.check(is_race_channel)
    async def update_comments(self, ctx, race_id: str) -> None:
        '''Race.update_race_comments()'''

        msg = f'Could not find race {race_id}'
        if race := self.races.get(race_id, None):
            if race.finished:
                await race.update_race_comments()
                msg = f'Updated race {race_id}'
            else:
                msg = f'Race {race_id} is not finished.'

        await ctx.send(msg)

    @commands.command()
    @commands.check(is_race_channel)
    async def spoiler(self, ctx, race_id: str) -> None:
        '''Marks the race as a spoiler

        Spoiler means that when the race results are posted in discord, it will
        be wrapped in ||.
        '''

        msg = f'Could not find race {race_id}'
        if race := self.races.get(race_id, None):
            race.spoiler = True
            msg = f'Race {race_id} has been marked as a spoiler.'

        await ctx.send(msg)

    @commands.command()
    @commands.check(is_race_channel)
    async def ignore(self, ctx, race_id: str, user: str) -> None:
        '''Ignores a user

        If a user is ignored, the bot will not wait for them to split before
        deciding whether or a split should be considered "finished" and
        announced to the rest of the racers.

        This is particularly useful when racers are not connected to the race
        room through livesplit, or if they are not visible to the other racers
        for whatever reason (comparisons are broken).
        '''

        msg = f'Could not find race {race_id}'
        if race := self.races.get(race_id, None):
            ignored = race.runners.user_ignore(user, True)
            if ignored:
                msg = f'Started ignoring user {user}'
            else:
                msg = f'Could not find user {user} in race {race_id}'
        await ctx.send(msg)

    @commands.command()
    @commands.check(is_race_channel)
    async def unignore(self, ctx, race_id: str, user: str) -> None:
        msg = f'Could not find race {race_id}'
        if race := self.races.get(race_id, None):
            ignored = race.runners.user_ignore(user, False)
            if ignored:
                msg = f'Started unignoring user {user}'
            else:
                msg = f'Could not find user {user} in race {race_id}'
        await ctx.send(msg)


    @commands.command(aliases = ['unwatch'])
    @commands.check(is_admin)
    @commands.check(is_race_channel)
    async def stop_watching(self, ctx, race_id: str) -> None:
        '''Manual command to stop watching a race

        Disconnects the ircs and removes the race from the database if it
        exists. This function mostly serves as a recovery for when the bot
        doesn't close gracefully and races are stale in the database.
        '''

        if race_db.check_race(race_id):
            race_db.delete_race(race_id)
            if race := self.races.get(race_id, None):
                await race.disconnect_ircs()
                race.finished = True
                msg = f'No longer watching race {race_id}'
            else:
                msg = f'Could not find race {race_id}'
        else:
            msg = f'Currently not tracking a race with id: {race_id}'
        await ctx.send(msg)

    @commands.command()
    @commands.check(is_race_channel)
    async def finish_race(self, ctx, race_id: str, user: str, time: str) -> None:
        '''Manual invocation to mark someone as finished

        Useful for if they are not connected through livesplit, or their
        connection to the irc room is broken (no comparisons).

        !finish_race <race_id> <user> <HH:MM:SS.XX>
        '''

        msg = f'Could not find race {race_id}.'
        if race := self.races.get(race_id, None):
            if runner := race.runners.get(user):
                if time.lower() == 'forfeit':
                    runner.update_status('Forfeit')
                    msg = f'Forfeited race for {user} for race {race_id}'
                    await race._check_all_splits_announcement()
                else:
                    ts = timestamp.parse_timestamp(f'RealTime {time}')
                    if ts.split_name:
                        await race.finish_race_for_user(runner.name, ts)
                        msg = f'Finished race for {runner.name} with time {time} for race {race_id}'
                    else:
                        msg = f'Invalid timestamp format: {time}'
            else:
                msg = f'Could not find user {user}'

        await ctx.send(msg)

    @commands.command()
    @commands.check(is_admin)
    @commands.check(is_race_channel)
    async def kill(self, ctx) -> None:
        '''Manual kill switch. Also removes all current race references'''

        logger.info(f'Bot shutting down')
        logger.info('Deleting races:')
        count = 0
        for race_id, race in self.races.items():
            logger.info(f'\t{race.race_id}')
            if race_db.check_race_is_finished(race_id):
                logger.info('\t\trace_db obj is finished')
                continue
            race_db.delete_race(race_id)
            if race.finished:
                logger.info('\t\trace is finished')
                continue
            count += 1
        for chat in {self.srl_irc, self.twitch_irc}:
            if chat and chat.alive:
                await chat.disconnect('discord')
        await ctx.send(f'Bot is shutting down after unwatching {count} races')
        await self.bot.close()

    @commands.command()
    @commands.check(is_race_channel)
    async def racebot_info(self, ctx) -> None:
        await ctx.send(self.get_info())

    def get_info(self) -> str:
        return '''
        Usage is `!watch <user>` to start watching a race.
After all the racers in a watched race have finished or skipped a split, a message will be sent to all the racers' twitch channels for the current standings in the race.
For you to receive messages, you'll have to connect your twitch account to SRL.

One feature of this bot is that if you type `!standings` in your twitch chat, it will post the current latest split of all the racers in order.

Another key feature of this bot is the ability to create a subset of racers to watch.
It's not uncommon in a big race that one or two people might be very far behind the leaders, or someone's livesplit comparisons are not working, or they are not even joining through livesplit. In these cases, the bot can be very delayed, or even not work properly when posting splits to everyone's channel.

To counter this, racers have the ability to list a subset of watchers that they would like to report off of.
If you type `!watch <user1>, <user2>...` in twitch chat, you can select a list of racers that you want to start watching.
Example, `!watch arayalol, hwangbroxd, franchewbacca`. Note that you are not automatically added to your own watchlist, but you can list yourself and it will work properly.

If you want to stop seeing the subset list messages, you use `!reset_watchlist`

For the described cases above, someone will have to manually enter their time with a commmand to get final results posted.
Use `!finish_race <race_id> <user> <time>`, where <time> is formatted as `HH:MM:SS.MS`
For example, `!finish_race uvlfr hwangbroxd 02:06:31.38`

In these cases, it also might be useful to have the bot ignore this user instead of waiting for splits that are never coming.
For this, use `!ignore <race_id> <user>`

If you would like to skip seeing messages altogether, you can use `!blacklist <user>` to put yourself on the blacklist, or `!unblacklist <user>` to take yourself off.'''

    @commands.command()
    @commands.check(is_race_channel)
    async def blacklist(self, ctx, user: str) -> None:
        blacklist.add_user(user)
        await ctx.send(f'User {user} has been added to the blacklist. This twitch channel will no longer receive race updates.')

    @commands.command()
    @commands.check(is_race_channel)
    async def unblacklist(self, ctx, user: str) -> None:
        blacklist.remove_user(user)
        await ctx.send(f'User {user} has been removed from the blacklist.')

    @commands.command()
    @commands.check(is_race_channel)
    async def silence_race(self, ctx, race_id: str) -> None:
        '''Marks a race as silenced

        A silenced race will not post automatically to any twitch chat, but
        can still be used to query via !standings.
        Mostly useful for if you want the bot to report "accurate" results
        but might not necessarily want the bot posting as a distraction.
        '''

        msg = f'Could not find race {race_id}.'
        if race := self.races.get(race_id, None):
            race.silenced = True
            msg = f'Race {race_id} has been silenced.'

        await ctx.send(msg)

    @commands.command()
    @commands.check(is_race_channel)
    async def unsilence_race(self, ctx, race_id: str) -> None:
        msg = f'Could not find race {race_id}.'
        if race := self.races.get(race_id, None):
            race.silenced = False
            msg = f'Race {race_id} has been unsilenced.'

        await ctx.send(msg)

    @commands.command()
    @commands.check(is_race_channel)
    async def post_results(self, ctx, race_id: str) -> None:
        '''Posts the results of a race to discord'''

        msg = f'Could not find race {race_id}.'
        if race := self.races.get(race_id, None):
            await race.update_race()
            msg = f'Race {race_id} results:\n\n' + '\n'.join(race.runners.overall_standings_list(True, True))

        await ctx.send(msg)

    @commands.command()
    @commands.check(is_admin)
    @commands.check(is_race_channel)
    async def edit_message(self, ctx, ch_id, msg_id, text):
        # ch_id msg_id are ints, text is wrapped in quotes
        print(ch_id, msg_id, text)
        ch = self.bot.get_channel(int(ch_id))
        msg = await ch.fetch_message(int(msg_id))

        await msg.edit(content=text)

    async def send_message(self, msg: str, channel: int) -> Message:
        '''Send a message in a given discord channel

        Returns the discord message object so it can be edited later
        '''

        ch = self.bot.get_channel(channel)
        msg_obj = await ch.send(msg)
        return msg_obj

    async def check_race_for_user(self, user: str) -> Race:
        '''Returns a race that contains a given user/runner'''
        ret = None
        for race in self.races.values():
            if not race.finished:
                if race.runners.get(user) or user in race.twitch_irc_watchers:
                    ret = race
        return ret

    async def check_race_for_watcher(self, watcher: str, race_id: str) -> bool:
        '''Returns true if the user is a watcher in a different race'''
        return any(watcher in race.twitch_irc_watchers for race in self.races.values() if not race.finished and race.race_id != race_id)


def run_discord_bot():
    bot = commands.Bot(command_prefix='!')

    @bot.event
    async def on_ready():
        logger.info(f'{bot.user.name} has connected to Discord!')
        logger.info('Currently in the following discords:')
        for guild in bot.guilds:
            logger.info(f'    {guild.name}')

    @bot.event
    async def on_message(message):
        if bot.user.mentioned_in(message):
            # thinking if slayer pings bot
            if message.author.id == 165711439296724992:
                await message.add_reaction('\U0001F914')
            # shark if araya pings bot
            elif message.author.id == 225016103812857856:
                await message.add_reaction('<:arayalEloShark:745259134991073330>')
            # partying face if anyone pings bot
            else:
                await message.add_reaction('\U0001F973')

        # thinking if slayer types in #race-bot
        if message.author.id == 165711439296724992 and message.channel.id == cfg.RACE_BOT_CHANNEL_ID:
            await message.add_reaction('\U0001F914')

        await bot.process_commands(message)

    bot.add_cog(DiscordBot(bot))
    bot.run(cfg.DISCORD_TOKEN)

if __name__ == '__main__':
    run_discord_bot()
