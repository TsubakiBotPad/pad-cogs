import discord

from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import *

import logging
import os
import asyncio
import time
from random import randint
from math import ceil

from rpadutils import CogSettings

log = logging.getLogger("red.scheduler")
log.setLevel(logging.INFO)


class Event:
    def __init__(self, data=None):
        self.name = data.pop('name')
        self.channel = data.pop('channel')
        self.server = data.pop('server')
        self.author = data.pop('author')
        self.command = data.pop('command')
        self.timedelta = data.pop('timedelta')
        self.repeat = data.pop('repeat')
        self.starttime = data.pop('starttime', None)

    def __lt__(self, other):
        my_sig = "{}-{}-{}-{}".format(self.timedelta, self.name,
                                      self.starttime, self.channel)
        other_sig = "{}-{}-{}-{}".format(other.timedelta, other.name,
                                         other.starttime, other.channel)
        return hash(my_sig) < hash(other_sig)


class Scheduler(commands.Cog):
    """Schedules commands to run every so often.
    Times are formed as follows: 1s, 2m, 3h, 5d, 1w
    """

    def __init__(self, bot):
        self.bot = bot

        self.config = Config.get_conf(self, identifier=537367732)
        self.config.register_guild(events=[])  # We should use this, but aaaa

        self.settings = SchedulerSettings("scheduler")
        self.events = self.settings.getevents()
        self.queue = asyncio.PriorityQueue(loop=bot.loop)
        self.queue_lock = asyncio.Lock()
        self.to_kill = {}
        self._load_events()

    def save_events(self):
        self.settings.setevents(self.events)

    def _load_events(self):
        # for entry in the self.events make an Event
        for server in self.events:
            for name, event in self.events[server].items():
                ret = {}
                ret['server'] = server
                ret.update(event)
                e = Event(ret)
                self.bot.loop.create_task(self._put_event(e))

    async def _put_event(self, event, fut=None, offset=None):
        if fut is None:
            now = int(time.time())
            if event.repeat:
                diff = now - event.starttime
                fut = ((ceil(diff / event.timedelta) * event.timedelta) +
                       event.starttime)
            else:
                fut = now + event.timedelta
        if offset:
            fut += offset
        await self.queue.put((fut, event))
        log.debug('Added "{}" to the scheduler queue at {}'.format(event.name,
                                                                   fut))

    async def _add_event(self, name, command,
                         dest_server: discord.Guild,
                         dest_channel: discord.TextChannel,
                         author: discord.User,
                         timedelta, repeat=False):
        dest_server = dest_server.id
        dest_channel = dest_channel.id
        author = author.id

        if dest_server not in self.events:
            self.events[dest_server] = {}

        event_dict = {'name': name,
                      'channel': dest_channel,
                      'author': author,
                      'command': command,
                      'timedelta': timedelta,
                      'repeat': repeat}

        log.debug('event dict:\n\t{}'.format(event_dict))

        now = int(time.time())
        event_dict['starttime'] = now
        self.events[dest_server][name] = event_dict.copy()

        event_dict['server'] = dest_server
        e = Event(event_dict.copy())
        await self._put_event(e)

        self.save_events()

    async def _remove_event(self, name, server):
        async with self.queue_lock:
            events = []
            while self.queue.qsize() != 0:
                time, event = await self.queue.get()
                if not (name == event.name and server.id == event.server):
                    events.append((time, event))

            for event in events:
                await self.queue.put(event)
            self.queue_lock.release()

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def scheduler(self, ctx):
        pass

    @scheduler.command()
    async def add(self, ctx, time_interval, *, command):
        """Add a command to run in [time_interval] seconds.
        Times are formed as follows: 1s, 2m, 3h, 5d, 1w
        """
        channel = ctx.channel
        server = ctx.guild
        author = ctx.author
        name = command.lower()
        try:
            s = self._parse_time(time_interval)
            log.debug('run command in {}s'.format(s))
        except:
            await self.bot.send_cmd_help(ctx)
            return
        if s < 30:
            await ctx.send('yeah I can\'t do that, your time'
                                 ' interval is waaaay too short and I\'ll'
                                 ' likely get rate limited. Try going above'
                                 ' 30 seconds.')
            return
        log.info('add {} "{}" to {} on {} in {}s'.format(
            name, command, channel.name, server.name, s))
        await self._add_event(name, command, server, channel, author, s)
        await ctx.send('I will run "{}" in {}s'.format(command, s))

    @scheduler.command()
    async def repeat(self, ctx, name, time_interval, *, command):
        """Add a command to run every [time_interval] seconds.
        Times are formed as follows: 1s, 2m, 3h, 5d, 1w
        """
        channel = ctx.channel
        server = ctx.guild
        author = ctx.author
        name = name.lower()
        try:
            s = self._parse_time(time_interval)
            log.debug('run command in {}s'.format(s))
        except:
            await self.bot.send_cmd_help(ctx)
            return
        if s < 30:
            await ctx.send('yeah I can\'t do that, your time'
                                 ' interval is waaaay too short and I\'ll'
                                 ' likely get rate limited. Try going above'
                                 ' 30 seconds.')
            return
        log.info('add {} "{}" to {} on {} every {}s'.format(
            name, command, channel.name, server.name, s))
        await self._add_event(name, command, server, channel, author, s, True)
        await ctx.send('"{}" will run "{}" every {}s'.format(name, command, s))

    @scheduler.command()
    async def remove(self, ctx, name):
        """Removes scheduled command from running.
        """
        server = ctx.guild
        name = name.lower()
        if server.id not in self.events:
            await ctx.send('No events are scheduled for this server.')
            return
        if name not in self.events[server.id]:
            await ctx.send('That event does not exist on this server.')
            return

        del self.events[server.id][name]
        await self._remove_event(name, server)
        self.save_events()
        await ctx.send('"{}" has successfully been removed but'
                           ' it may run once more.'.format(name))

    @scheduler.command()
    async def list(self, ctx):
        """Lists all repeated commands
        """
        server = ctx.guild
        if server.id not in self.events:
            await ctx.send('No events scheduled for this server.')
            return
        elif len(self.events[server.id]) == 0:
            await ctx.send('No events scheduled for this server.')
            return
        mess = "Names:\n\t"
        mess += "\n\t".join(sorted(self.events[server.id].keys()))
        await ctx.send(box(mess))

    def _parse_time(self, time):
        translate = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        timespec = time[-1]
        if timespec.lower() not in translate:
            raise ValueError
        timeint = int(time[:-1])
        return timeint * translate.get(timespec)

    def run_coro(self, event):
        channel = self.bot.get_channel(event.channel)
        try:
            server = channel.guild
            prefix = self.bot.settings.get_prefixes(server)[0]
        except AttributeError:
            log.debug("Channel no longer found, not running scheduled event.")
            return
        data = {}
        data['timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime())
        data['id'] = randint(10**(17), (10**18) - 1)
        data['content'] = prefix + event.command
        data['channel'] = self.bot.get_channel(event.channel)
        data['author'] = {'id': event.author}
        data['nonce'] = randint(-2**32, (2**32) - 1)
        data['channel_id'] = event.channel
        data['reactions'] = []
        fake_message = discord.Message(**data)
        # coro = self.bot.process_commands(fake_message)
        log.info("Running '{}' in {}".format(event.name, event.server))
        # self.bot.loop.create_task(coro)
        self.bot.dispatch('message', fake_message)

    async def queue_manager(self):
        while self == self.bot.get_cog('Scheduler'):
            async with self.queue_lock:
                if self.queue.qsize() != 0:
                    next_time, next_event = await self.queue.get()
                    diff = max(next_time-int(time.time()), 0)
                    if diff < 30:
                        log.debug('scheduling call of "{}" in {}s'.format(
                            next_event.name, diff))
                        fut = self.bot.loop.call_later(diff, self.run_coro,
                                                       next_event)
                        self.to_kill[next_time] = fut
                        if next_event.repeat:
                            await self._put_event(next_event, next_time,
                                                  next_event.timedelta)
                        else:
                            del self.events[next_event.server][next_event.name]
                            self.save_events()
                    else:
                        log.debug('Will run {} "{}" in {}s'.format(
                            next_event.name, next_event.command, diff))
                        await self._put_event(next_event, next_time)

            to_delete = []
            for start_time, old_command in self.to_kill.items():
                if time.time() > start_time + 30:
                    old_command.cancel()
                    to_delete.append(start_time)
            for item in to_delete:
                del self.to_kill[item]

            await asyncio.sleep(5)
        log.debug('manager dying')
        while self.queue.qsize() != 0:
            await self.queue.get()
        while len(self.to_kill) != 0:
            curr = self.to_kill.pop()
            curr.cancel()


def check_folder():
    if not os.path.exists('data/scheduler'):
        os.mkdir('data/scheduler')


def check_files():
    f = 'data/scheduler/events.json'
    if not os.path.exists(f):
        fileIO(f, 'save', {})


class SchedulerSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'events': {},
        }
        return config

    def getevents(self):
        return self.bot_settings['events']

    def setevents(self, events):
        self.bot_settings['events'] = events
        self.save_settings()
