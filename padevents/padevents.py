import asyncio
import datetime
import logging
import re
from collections import defaultdict
from datetime import timedelta
from enum import Enum
from io import BytesIO
from typing import TYPE_CHECKING

import discord
import itertools
import prettytable
import pytz
from redbot.core import checks
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import box, pagify
from tsutils import CogSettings, confirm_message, normalize_server_name, DummyObject, is_donor

if TYPE_CHECKING:
    from dadguide.models.scheduled_event_model import ScheduledEventModel


def user_is_donor(ctx, only_patron=False):
    if ctx.author.id in ctx.bot.owner_ids:
        return True
    donationcog = ctx.bot.get_cog("Donations")
    if not donationcog:
        return False
    return donationcog.is_donor(ctx, only_patron)


logger = logging.getLogger('red.padbot-cogs.padevents')

SUPPORTED_SERVERS = ["JP", "NA", "KR"]
GROUPS = ['red', 'blue', 'green']


class PadEvents(commands.Cog):
    """Pad Event Tracker"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.settings = PadEventSettings("padevents")
        self.config = Config.get_conf(self, identifier=940373775)
        self.config.register_guild(pingroles={})
        self.config.register_user(dmevents=[])

        # Load event data
        self.events = list()
        self.started_events = set()
        self.rolepinged_events = set()

        self.fake_uid = -999

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    def cog_unload(self):
        # Manually nulling out database because the GC for cogs seems to be pretty shitty
        self.events = list()
        self.started_events = set()

    async def reload_padevents(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('PadEvents'):
            try:
                await self.refresh_data()
                logger.info('Done refreshing PadEvents')
            except Exception as ex:
                logger.exception("reload padevents loop caught exception " + str(ex))

            await asyncio.sleep(60 * 60 * 1)

    async def refresh_data(self):
        dg_cog = self.bot.get_cog('Dadguide')
        await dg_cog.wait_until_ready()
        scheduled_events = dg_cog.database.get_all_events()

        new_events = []
        for se in scheduled_events:
            try:
                db_context = self.bot.get_cog("Dadguide").database
                new_events.append(Event(se, db_context))
            except Exception as ex:
                logger.exception("Refresh error:")

        self.events = new_events
        self.started_events = {ev.key for ev in new_events if ev.is_started()}
        self.rolepinged_events = set()

    async def check_started(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('PadEvents'):
            try:
                events = filter(lambda e: e.key not in self.started_events, self.events)
                for event in events:
                    for gid, data in (await self.config.all_guilds()).items():
                        guild = self.bot.get_guild(gid)
                        if guild is None:
                            continue
                        for key, aep in data.get('pingroles', {}).items():
                            if event.start_from_now_sec() > aep['offset'] * 60 \
                                    or not aep['enabled'] \
                                    or event.server != aep['server'] \
                                    or (key, event.key) in self.rolepinged_events:
                                continue
                            elif aep['regex']:
                                matches = re.search(aep['searchstr'], event.clean_dungeon_name)
                            else:
                                matches = aep['searchstr'].lower() in event.clean_dungeon_name.lower()

                            self.rolepinged_events.add((key, event.key))
                            if matches:
                                index = GROUPS.index(event.group)
                                channel = guild.get_channel(aep['channels'][index])
                                if channel is not None:
                                    role = guild.get_role(aep['roles'][index])
                                    ment = role.mention if role else ""
                                    offsetstr = ""
                                    if aep['offset']:
                                        offsetstr = " in {} minute(s)".format(aep['offset'])
                                    try:
                                        await channel.send("{}{} {}".format(event.name_and_modifier, offsetstr, ment),
                                                           allowed_mentions=discord.AllowedMentions(roles=True))
                                    except Exception:
                                        logger.exception("Failed to send AEP in channel {}".format(channel.id))

                    for uid, data in (await self.config.all_users()).items():
                        user = self.bot.get_user(uid)
                        if user is None:
                            continue
                        for aed in data.get('dmevents', []):
                            if event.start_from_now_sec() > aed['offset'] * 60 \
                                    or (event.group not in (aed['group'], None)) \
                                    or event.server != aed['server'] \
                                    or (aed['key'], event.key) in self.rolepinged_events:
                                continue
                            self.rolepinged_events.add((aed['key'], event.key))
                            if aed['searchstr'].lower() in event.clean_dungeon_name.lower():
                                offsetstr = " starts now!"
                                if aed['offset']:
                                    offsetstr = " starts in {} minute(s)!".format(aed['offset'])
                                try:
                                    await user.send(event.clean_dungeon_name + offsetstr)
                                except Exception:
                                    logger.exception("Failed to send AED to user {}".format(user.id))

                events = filter(lambda e: e.is_started() and e.key not in self.started_events, self.events)
                daily_refresh_servers = set()
                for event in events:
                    self.started_events.add(event.key)
                    if event.event_type in [EventType.Guerrilla, EventType.GuerrillaNew, EventType.SpecialWeek,
                                            EventType.Week]:
                        for gr in list(self.settings.list_guerrilla_reg()):
                            if event.server == gr['server']:
                                try:
                                    channel = self.bot.get_channel(int(gr['channel_id']))
                                    if channel is None:
                                        continue

                                    role_name = '{}_group_{}'.format(event.server, event.group_long_name())
                                    role = channel.guild.get_role(role_name)
                                    if role and role.mentionable:
                                        message = "{} `: {} is starting`".format(role.mention, event.name_and_modifier)
                                    else:
                                        message = box(
                                            "Server " + event.server + ", group " + event.group_long_name() +
                                            " : " + event.name_and_modifier
                                        )

                                    await channel.send(message, allowed_mentions=discord.AllowedMentions(roles=True))
                                except Exception as ex:
                                    # self.settings.remove_guerrilla_reg(gr['channel_id'], gr['server'])
                                    logger.exception("caught exception while sending guerrilla msg:")

                    else:
                        if event.technical not in [DungeonType.Normal]:
                            msg = self.make_active_text(event.server)
                            for daily_registration in list(self.settings.list_daily_reg()):
                                try:
                                    if event.server == daily_registration['server']:
                                        await self.page_output(self.bot.get_channel(daily_registration['channel_id']),
                                                               msg, channel_id=daily_registration['channel_id'])
                                        logger.info("daily_reg server")
                                except Exception as ex:
                                    # self.settings.remove_daily_reg(
                                    #   daily_registration['channel_id'], daily_registration['server'])
                                    logger.exception("caught exception while sending daily msg:")

            except Exception as ex:
                logger.exception("caught exception while checking guerrillas:")

            await asyncio.sleep(10)
        logger.info("done check_started (cog probably unloaded)")

    @commands.group(aliases=['pde'])
    @checks.mod_or_permissions(manage_guild=True)
    async def padevents(self, ctx):
        """PAD event tracking"""

    @padevents.command()
    @checks.is_owner()
    async def testevent(self, ctx, server, seconds: int = 0):
        server = normalize_server_name(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        dg_cog = self.bot.get_cog('Dadguide')
        await dg_cog.wait_until_ready()
        # TODO: Don't use this awful importing hack
        dg_module = __import__('.'.join(dg_cog.__module__.split('.')[:-1]) + ".models.scheduled_event_model")
        timestamp = int((datetime.datetime.now(pytz.utc) + timedelta(seconds=seconds)).timestamp())
        self.fake_uid -= 1

        te = dg_module.models.scheduled_event_model.ScheduledEventModel(
            event_id=self.fake_uid,
            server_id=SUPPORTED_SERVERS.index(server),
            event_type_id=EventType.Guerrilla.value,
            start_timestamp=timestamp,
            end_timestamp=timestamp + 60,
            group_name='red',
            dungeon_model=DummyObject(
                name_en='fake_dungeon_name',
                clean_name_en='fake_dungeon_name',
                dungeon_type=DungeonType.Unknown7,
                dungeon_id=1,
            )
        )
        self.events.append(Event(te, self.bot.get_cog('Dadguide').database))
        await ctx.tick()

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addchannel(self, ctx, server):
        server = normalize_server_name(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        channel_id = ctx.channel.id
        if self.settings.check_guerrilla_reg(channel_id, server):
            await ctx.send("Channel already active.")
            return

        self.settings.add_guerrilla_reg(channel_id, server)
        await ctx.send("Channel now active.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmchannel(self, ctx, server):
        server = normalize_server_name(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        channel_id = ctx.channel.id
        if not self.settings.check_guerrilla_reg(channel_id, server):
            await ctx.send("Channel is not active.")
            return

        self.settings.remove_guerrilla_reg(channel_id, server)
        await ctx.send("Channel deactivated.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addchanneldaily(self, ctx, server):
        server = normalize_server_name(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        channel_id = ctx.channel.id
        if self.settings.check_daily_reg(channel_id, server):
            await ctx.send("Channel already active.")
            return

        self.settings.add_daily_reg(channel_id, server)
        await ctx.send("Channel now active.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmchanneldaily(self, ctx, server):
        server = normalize_server_name(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        channel_id = ctx.channel.id
        if not self.settings.check_daily_reg(channel_id, server):
            await ctx.send("Channel is not active.")
            return

        self.settings.remove_daily_reg(channel_id, server)
        await ctx.send("Channel deactivated.")

    @commands.group(aliases=['aep'])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def autoeventping(self, ctx):
        """Auto Event Pings"""

    @autoeventping.command(name="add")
    async def aep_add(self, ctx, key, server=None, searchstr=None, red: discord.Role = None, blue: discord.Role = None,
                      green: discord.Role = None):
        """Add a new autoeventping"""
        if green is None and server is not None:
            await ctx.send("Multi-word keys must be in quotes.")
            return

        default = {
            'roles': [None, None, None],
            'channels': [None, None, None],
            'server': 'NA',
            'searchstr': None,
            'regex': False,
            'enabled': False,
            'offset': 0,
        }

        if green is not None:
            server = normalize_server_name(server)
            if server not in SUPPORTED_SERVERS:
                await ctx.send("Unsupported server, pick one of NA, KR, JP")
                return
            default.update({
                'roles': [red.id, blue.id, green.id],
                'channels': [ctx.channel.id] * 3,
                'server': server,
                'searchstr': searchstr,
                'enabled': True,
            })

        async with self.config.guild(ctx.guild).pingroles() as pingroles:
            pingroles[key] = default
        await ctx.tick()

    @autoeventping.command(name="remove", aliases=['rm', 'delete'])
    async def aep_remove(self, ctx, *, key):
        """Remove an autoeventping"""
        async with self.config.guild(ctx.guild).pingroles() as pingroles:
            if key not in pingroles:
                await ctx.send("That key does not exist.")
                return
            del pingroles[key]
        await ctx.tick()

    @autoeventping.command(name="show")
    async def aep_show(self, ctx, *, key):
        """Show specifics of an autoeventping"""
        pingroles = await self.config.guild(ctx.guild).pingroles()
        if key not in pingroles:
            await ctx.send("That key does not exist.")
            return
        roles = [ctx.guild.get_role(role).mention
                 if ctx.guild.get_role(role) is not None
                 else "No Role"
                 for role
                 in pingroles[key]['roles']
                 ]
        chans = [ctx.bot.get_channel(c).mention
                 if ctx.bot.get_channel(c) is not None
                 else "No Channel"
                 for c
                 in pingroles[key]['channels']
                 ]
        pr = (f"{key} ({'enabled' if pingroles[key]['enabled'] else 'disabled'})\n"
              f"\tSearch String: '{pingroles[key]['searchstr']}' {'(regex search)' * pingroles[key]['regex']}\n"
              f"\tServer: {pingroles[key]['server']}\n"
              f"\tRed: {roles[0]} (In {chans[0]})\n"
              f"\tBlue: {roles[1]} (In {chans[1]})\n"
              f"\tGreen: {roles[2]} (In {chans[2]})\n"
              f"\tOffset: {pingroles[key]['offset']} minutes")
        await ctx.send(pr)

    @autoeventping.command(name="list")
    async def aep_list(self, ctx):
        """List all autoeventpings"""
        pingroles = await self.config.guild(ctx.guild).pingroles()
        if len(pingroles) == 0:
            await ctx.send('You have no auto event pings configured currently!')
            return
        await ctx.send(box('\n'.join(pingroles)))

    @autoeventping.group(name="set")
    async def aep_set(self, ctx):
        """Sets specific parts of an autoeventping"""

    async def aepc(self, ctx, key, k, f):
        async with self.config.guild(ctx.guild).pingroles() as pingroles:
            if key not in pingroles:
                await ctx.send("That key does not exist.")
                return
            pingroles[key][k] = f(pingroles[key][k])

    async def aeps(self, ctx, key, k, v):
        await self.aepc(ctx, key, k, lambda x: v)

    async def aepg(self, ctx, key):
        pingroles = await self.config.guild(ctx.guild).pingroles()
        if key not in pingroles:
            await ctx.send("That key does not exist.")
            return
        return pingroles[key]

    @aep_set.command(name="channel")
    async def aep_s_channel(self, ctx, key, channel: discord.TextChannel):
        """Sets channel to ping for all groups"""
        await self.aeps(ctx, key, 'channels', [channel.id] * 3)
        await ctx.tick()

    @aep_set.command(name="redchannel")
    async def aep_s_redchannel(self, ctx, key, channel: discord.TextChannel):
        """Sets channel to ping when event is red"""
        await self.aepc(ctx, key, 'channels', lambda x: [channel.id, x[1], x[2]])
        await ctx.tick()

    @aep_set.command(name="bluechannel")
    async def aep_s_bluechannel(self, ctx, key, channel: discord.TextChannel):
        """Sets channel to ping when event is blue"""
        await self.aepc(ctx, key, 'channels', lambda x: [x[0], channel.id, x[2]])
        await ctx.tick()

    @aep_set.command(name="greenchannel")
    async def aep_s_greenchannel(self, ctx, key, channel: discord.TextChannel):
        """Sets channel to ping when event is green"""
        await self.aepc(ctx, key, 'channels', lambda x: [x[0], x[1], channel.id])
        await ctx.tick()

    @aep_set.command(name="roles")
    async def aep_s_roles(self, ctx, key, red: discord.Role, blue: discord.Role, green: discord.Role):
        """Sets roles to ping"""
        await self.aeps(ctx, key, 'roles', [red.id, blue.id, green.id])
        await ctx.tick()

    @aep_set.command(name="redrole")
    async def aep_s_redrole(self, ctx, key, role: discord.Role):
        """Sets role to ping when event is red"""
        await self.aepc(ctx, key, 'roles', lambda x: [role.id, x[1], x[2]])
        await ctx.tick()

    @aep_set.command(name="bluerole")
    async def aep_s_bluerole(self, ctx, key, role: discord.Role):
        """Sets role to ping when event is blue"""
        await self.aepc(ctx, key, 'roles', lambda x: [x[0], role.id, x[2]])
        await ctx.tick()

    @aep_set.command(name="greenrole")
    async def aep_s_greenrole(self, ctx, key, role: discord.Role):
        """Sets role to ping when event is green"""
        await self.aepc(ctx, key, 'roles', lambda x: [x[0], x[1], role.id])
        await ctx.tick()

    @aep_set.command(name="server")
    async def aep_s_server(self, ctx, key, server):
        """Sets which server to listen to events in"""
        server = normalize_server_name(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return
        await self.aeps(ctx, key, 'server', server)
        await ctx.tick()

    @aep_set.command(name="searchstr")
    async def aep_s_searchstr(self, ctx, key, *, searchstr):
        """Sets what string is tested against event name"""
        searchstr = searchstr.strip('"')
        if (await self.aepg(ctx, key))['regex']:
            try:
                re.compile(searchstr)
            except re.error:
                await ctx.send("Invalid regex searchstr. (`{}`)".format(searchstr))
                return
        await self.aeps(ctx, key, 'searchstr', searchstr)
        await ctx.tick()

    @aep_set.command(name="regex")
    async def aep_s_regex(self, ctx, key, regex: bool):
        """Sets whether searchstr is calculated via regex"""
        if regex:
            try:
                re.compile((await self.aepg(ctx, key))['searchstr'])
            except re.error:
                await ctx.send("Invalid regex searchstr. (`{}`)".format((await self.aepg(ctx, key))['searchstr']))
                return
        await self.aeps(ctx, key, 'regex', regex)
        await ctx.tick()

    @aep_set.command(name="enabled", aliases=['enable'])
    async def aep_s_enabled(self, ctx, key, enabled: bool = True):
        """Sets whether or not ping is enabled"""
        await self.aeps(ctx, key, 'enabled', enabled)
        await ctx.tick()

    @aep_set.command(name="disabled", aliases=['disable'])
    async def aep_s_disabled(self, ctx, key, disabled: bool = True):
        """Sets whether or not ping is disabled"""
        await self.aeps(ctx, key, 'enabled', not disabled)
        await ctx.tick()

    @aep_set.command(name="offset")
    async def aep_s_disabled(self, ctx, key, offset: int):
        """Sets how many minutes before event should ping happen"""
        if offset < 0:
            await ctx.send("Offset cannot be negative.")
            return
        await self.aeps(ctx, key, 'offset', offset)
        await ctx.tick()

    @commands.group(aliases=['aed'])
    async def autoeventdm(self, ctx):
        """Auto Event DMs"""

    @autoeventdm.command(name="add")
    async def aed_add(self, ctx, server, searchstr, group, time_offset: int = 0):
        """Add a new autoeventdm"""
        server = normalize_server_name(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return
        group = group.lower()
        if group not in GROUPS:
            await ctx.send("Unsupported group, pick one of red, blue, green")
            return
        if time_offset and not user_is_donor(ctx):
            await ctx.send("You must be a donor to set a time offset!")
            return
        if time_offset < 0:
            await ctx.send("Offset cannot be negative")
            return

        default = {
            'key': datetime.datetime.now().timestamp(),
            'server': server,
            'group': group,
            'searchstr': searchstr,
            'offset': time_offset,
        }

        async with self.config.user(ctx.author).dmevents() as dmevents:
            dmevents.append(default)
        await ctx.tick()

    @autoeventdm.command(name="remove", aliases=['rm', 'delete'])
    async def aed_remove(self, ctx, index: int):
        """Remove an autoeventdm"""
        async with self.config.user(ctx.author).dmevents() as dmevents:
            if not 0 < index <= len(dmevents):
                await ctx.send("That isn't a valid index.")
                return
            if not await confirm_message(ctx, ("Are you sure you want to delete autoeventdm with searchstring '{}'"
                                               "").format(dmevents[index - 1]['searchstr'])):
                return
            dmevents.pop(index - 1)
        await ctx.tick()

    @autoeventdm.command(name="list")
    async def aed_list(self, ctx):
        """List current autoeventdms"""
        dmevents = await self.config.user(ctx.author).dmevents()
        msg = "\n".join("{}. {}".format(c, aed['searchstr']) for c, aed in enumerate(dmevents, 1))
        if msg:
            await ctx.send(box(msg))
        else:
            await ctx.send("You have no autoeventdms set up.")

    @autoeventdm.command(name="purge")
    async def aed_purge(self, ctx):
        """Remove an autoeventdm"""
        if not await self.config.user(ctx.author).dmevents():
            await ctx.send("You don't have any autoeventdms.")
            return
        if not await confirm_message(ctx, "Are you sure you want to purge your autoeventdms?"):
            return
        await self.config.user(ctx.author).dmevents.set([])
        await ctx.tick()

    @autoeventdm.group(name="edit")
    async def aed_e(self, ctx):
        """Edit a property of the autoeventdm"""

    @is_donor()
    @aed_e.command(name="offset")
    async def aed_e_offset(self, ctx, index, offset):
        """(DONOR ONLY) Set time offset to an AED to allow you to prepare for a dungeon"""
        if offset < 0:
            await ctx.send("Offset cannot be negative")
            return
        async with self.config.user(ctx.author).dmevents() as dmevents:
            if not 0 < index <= len(dmevents):
                await ctx.send("That isn't a valid index.")
                return
            dmevents[index - 1]['offset'] = offset
        await ctx.tick()

    @aed_e.command(name="searchstr")
    async def aed_e_searchstr(self, ctx, index, *, searchstr):
        """Set search string of an autoeventdm"""
        searchstr = searchstr.strip('"')
        async with self.config.user(ctx.author).dmevents() as dmevents:
            if not 0 < index <= len(dmevents):
                await ctx.send("That isn't a valid index.")
                return
            dmevents[index - 1]['searchstr'] = searchstr
        await ctx.tick()

    @padevents.command()
    @checks.is_owner()
    async def listallchannels(self, ctx):
        msg = 'Following daily channels are registered:\n'
        msg += self.make_channel_list(self.settings.list_daily_reg())
        msg += "\n"
        msg += 'Following guerilla channels are registered:\n'
        msg += self.make_channel_list(self.settings.list_guerrilla_reg())
        await self.page_output(ctx, msg)

    @padevents.command()
    @checks.mod_or_permissions(manage_guild=True)
    async def listchannels(self, ctx):
        msg = 'Following daily channels are registered:\n'
        msg += self.make_channel_list(self.settings.list_daily_reg(), lambda c: c in ctx.guild.channels)
        msg += "\n"
        msg += 'Following guerilla channels are registered:\n'
        msg += self.make_channel_list(self.settings.list_guerrilla_reg(), lambda c: c in ctx.guild.channels)
        await self.page_output(ctx, msg)

    def make_channel_list(self, reg_list, filt=None):
        if filt is None:
            def filt(x):
                return x
        msg = ""
        for cr in reg_list:
            reg_channel_id = cr['channel_id']
            channel = self.bot.get_channel(int(reg_channel_id))
            if filt(channel):
                channel_name = channel.name if channel else 'Unknown(' + reg_channel_id + ')'
                server_name = channel.guild.name if channel else 'Unknown server'
                msg += "   " + cr['server'] + " : " + server_name + '(' + channel_name + ')\n'
        return msg

    @padevents.command()
    @checks.mod_or_permissions(manage_guild=True)
    async def active(self, ctx, server):
        server = normalize_server_name(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        msg = self.make_active_text(server)
        await self.page_output(ctx, msg)

    def make_active_text(self, server):
        server_events = EventList(self.events).with_server(server)
        active_events = server_events.active_only()
        pending_events = server_events.pending_only()
        available_events = server_events.available_only()

        msg = "Listing all events for " + server

        """
        special_events = active_events.with_type(
            EventType.Special).items_by_close_time()
        if len(special_events) > 0:
            msg += "\n\n" + self.make_active_output('Special Events', special_events)

        all_etc_events = active_events.with_type(EventType.Etc)

        etc_events = all_etc_events.with_dungeon_type(
            DungeonType.Etc).exclude_unwanted_events().items_by_close_time()
        if len(etc_events) > 0:
            msg += "\n\n" + self.make_active_output('Etc Events', etc_events)

        # Old-style guerrillas
        active_guerrilla_events = active_events.with_type(EventType.Guerrilla).items()
        if len(active_guerrilla_events) > 0:
            msg += "\n\n" + \
                   self.make_active_guerrilla_output('Active Guerrillas', active_guerrilla_events)

        guerrilla_events = pending_events.with_type(EventType.Guerrilla).items()
        if len(guerrilla_events) > 0:
            msg += "\n\n" + self.make_full_guerrilla_output('Guerrilla Events', guerrilla_events)

        # New-style guerrillas
        active_guerrilla_events = active_events.with_type(EventType.SpecialWeek).items()
        if len(active_guerrilla_events) > 0:
            msg += "\n\n" + \
                   self.make_active_guerrilla_output('Active Guerrillas', active_guerrilla_events)

        guerrilla_events = pending_events.with_type(EventType.SpecialWeek).items()
        if len(guerrilla_events) > 0:
            msg += "\n\n" + \
                   self.make_full_guerrilla_output(
                       'Guerrilla Events', guerrilla_events, starter_guerilla=True)
        """
        active_cdo_events = active_events.with_dungeon_type(DungeonType.CoinDailyOther).is_grouped(True).items()
        if len(active_cdo_events) > 0:
            msg += "\n\n" + \
                   self.make_active_output(
                       'Active Events', active_cdo_events)
        """
        cdo_events = pending_events.with_dungeon_type(DungeonType.CoinDailyOther).is_grouped(False).items()
        if len(cdo_events) > 0:
            msg += "\n\n" + \
                   self.make_active_output(
                       'Reward Events', cdo_events)
        """

        active_grouped_cdo_events = active_events.with_dungeon_type(DungeonType.CoinDailyOther).is_grouped().items()
        if len(active_grouped_cdo_events) > 0:
            msg += "\n\n" + \
                   self.make_active_guerrilla_output(
                       'Active Guerrillas', active_grouped_cdo_events)
        grouped_cdo_events = pending_events.with_dungeon_type(DungeonType.CoinDailyOther).is_grouped().items()
        if len(grouped_cdo_events) > 0:
            msg += "\n\n" + \
                   self.make_full_guerrilla_output(
                       'Guerrillas', grouped_cdo_events, starter_guerilla=True)

        active_etc_events = active_events.with_dungeon_type(DungeonType.Etc).items()
        if len(active_etc_events) > 0:
            msg += "\n\n" + \
                   self.make_active_output(
                       'Active Other Events', active_etc_events)
        """
        etc_events = pending_events.with_dungeon_type(DungeonType.Etc).items()
        if len(etc_events) > 0:
            msg += "\n\n" + \
                   self.make_active_output(
                       'Other Events', etc_events)
        """
        # clean up long headers
        msg = msg.replace('-------------------------------------', '-----------------------')

        return msg

    async def page_output(self, ctx, msg, channel_id=None, format_type=box):
        msg = msg.strip()
        msg = pagify(msg, ["\n"], shorten_by=20)
        for page in msg:
            try:
                if channel_id is None:
                    await ctx.send(format_type(page))
                else:
                    await self.bot.get_channel(int(channel_id)).send(format_type(page))
            except Exception as e:
                logger.exception("page output failed " + str(e), "tried to output: " + page)

    def make_active_output(self, table_name, event_list):
        tbl = prettytable.PrettyTable(["Time", table_name])
        tbl.hrules = prettytable.HEADER
        tbl.vrules = prettytable.NONE
        tbl.align[table_name] = "l"
        tbl.align["Time"] = "r"
        for e in event_list:
            tbl.add_row([e.end_from_now_full_min().strip(), e.name_and_modifier])
        return tbl.get_string()

    def make_active_guerrilla_output(self, table_name, event_list):
        tbl = prettytable.PrettyTable([table_name, "Group", "Time"])
        tbl.hrules = prettytable.HEADER
        tbl.vrules = prettytable.NONE
        tbl.align[table_name] = "l"
        tbl.align["Time"] = "r"
        for e in event_list:
            tbl.add_row([e.name_and_modifier, e.group, e.end_from_now_full_min().strip()])
        return tbl.get_string()

    def make_full_guerrilla_output(self, table_name, event_list, starter_guerilla=False):
        events_by_name = defaultdict(list)
        for event in event_list:
            events_by_name[event.name_and_modifier].append(event)

        rows = list()
        grps = ["RED", "BLUE", "GREEN"] if starter_guerilla else ["A", "B", "C", "D", "E"]
        for name, events in events_by_name.items():
            events = sorted(events, key=lambda e: e.open_datetime)
            events_by_group = defaultdict(list)
            for event in events:
                events_by_group[event.group.upper()].append(event)

            done = False
            while not done:
                did_work = False
                row = list()
                row.append(name)
                for g in grps:
                    grp_list = events_by_group[g]
                    if len(grp_list) == 0:
                        row.append("")
                    else:
                        did_work = True
                        event = grp_list.pop(0)
                        row.append(event.to_guerrilla_str())
                if did_work:
                    rows.append(row)
                else:
                    done = True

        col1 = "Pending"
        tbl = prettytable.PrettyTable([col1] + grps)
        tbl.align[col1] = "l"
        tbl.hrules = prettytable.HEADER
        tbl.vrules = prettytable.ALL

        for r in rows:
            tbl.add_row(r)

        header = "Times are PT below\n\n"
        return header + tbl.get_string() + "\n"

    @commands.command(aliases=['events'])
    async def eventsna(self, ctx):
        """Display upcoming daily events for NA."""
        await self.do_partial(ctx, 'NA')

    @commands.command()
    async def eventsjp(self, ctx):
        """Display upcoming daily events for JP."""
        await self.do_partial(ctx, 'JP')

    @commands.command()
    async def eventskr(self, ctx):
        """Display upcoming daily events for KR."""
        await self.do_partial(ctx, 'KR')

    async def do_partial(self, ctx, server):
        server = normalize_server_name(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        events = EventList(self.events)
        events = events.with_server(server)
        events = events.in_dungeon_type([DungeonType.Etc, DungeonType.CoinDailyOther])
        events = events.is_grouped()

        active_events = events.active_only().items_by_open_time(reverse=True)
        pending_events = events.pending_only().items_by_open_time(reverse=True)

        group_to_active_event = {e.group: e for e in active_events}
        group_to_pending_event = {e.group: e for e in pending_events}

        # active_events = list(group_to_active_event.values())
        # pending_events = list(group_to_pending_event.values())

        active_events.sort(key=lambda e: (GROUPS.index(e.group), e.open_datetime))
        pending_events.sort(key=lambda e: (GROUPS.index(e.group), e.open_datetime))

        if len(active_events) == 0 and len(pending_events) == 0:
            await ctx.send("No events available for " + server)
            return

        output = "Events for {}".format(server)

        if len(active_events) > 0:
            output += "\n\n" + "  Remaining Dungeon"
            for e in active_events:
                output += "\n" + e.to_partial_event(self)

        if len(pending_events) > 0:
            output += "\n\n" + "  PT    ET    ETA     Dungeon"
            for e in pending_events:
                output += "\n" + e.to_partial_event(self)

        for page in pagify(output):
            await ctx.send(box(page))


def make_channel_reg(channel_id, server):
    server = normalize_server_name(server)
    return {
        "channel_id": channel_id,
        "server": server
    }


class PadEventSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'guerrilla_regs': [],
            'daily_regs': [],
        }
        return config

    def list_guerrilla_reg(self):
        return self.bot_settings['guerrilla_regs']

    def add_guerrilla_reg(self, channel_id, server):
        self.list_guerrilla_reg().append(make_channel_reg(channel_id, server))
        self.save_settings()

    def check_guerrilla_reg(self, channel_id, server):
        return make_channel_reg(channel_id, server) in self.list_guerrilla_reg()

    def remove_guerrilla_reg(self, channel_id, server):
        if self.check_guerrilla_reg(channel_id, server):
            self.list_guerrilla_reg().remove(make_channel_reg(channel_id, server))
            self.save_settings()

    def list_daily_reg(self):
        return self.bot_settings['daily_regs']

    def add_daily_reg(self, channel_id, server):
        self.list_daily_reg().append(make_channel_reg(channel_id, server))
        self.save_settings()

    def check_daily_reg(self, channel_id, server):
        return make_channel_reg(channel_id, server) in self.list_daily_reg()

    def remove_daily_reg(self, channel_id, server):
        if self.check_daily_reg(channel_id, server):
            self.list_daily_reg().remove(make_channel_reg(channel_id, server))
            self.save_settings()


class Event:
    def __init__(self, scheduled_event: "ScheduledEventModel", db_context):
        self.db_context = db_context
        self.key = scheduled_event.event_id
        self.server = SUPPORTED_SERVERS[scheduled_event.server_id]
        self.open_datetime = scheduled_event.open_datetime
        self.close_datetime = scheduled_event.close_datetime
        self.group = scheduled_event.group_name
        self.dungeon = scheduled_event.dungeon
        self.dungeon_name = self.dungeon.name_en if self.dungeon else 'unknown_dungeon'
        self.event_name = ''  # scheduled_event.event.name if scheduled_event.event else ''

        self.clean_dungeon_name = self.dungeon.clean_name_en if self.dungeon else 'unknown_dungeon'
        self.clean_event_name = self.event_name.replace('!', '').replace(' ', '')

        self.name_and_modifier = self.clean_dungeon_name
        if self.clean_event_name != '':
            self.name_and_modifier += ', ' + self.clean_event_name

        self.event_type = EventType(scheduled_event.event_type_id)

        self.dungeon_type = DungeonType(self.dungeon.dungeon_type) if self.dungeon else DungeonType.Unknown

    def start_from_now_sec(self):
        now = datetime.datetime.now(pytz.utc)
        return (self.open_datetime - now).total_seconds()

    def end_from_now_sec(self):
        now = datetime.datetime.now(pytz.utc)
        return (self.close_datetime - now).total_seconds()

    def is_started(self):
        """True if past the open time for the event."""
        return self.start_from_now_sec() <= 0

    def is_finished(self):
        """True if past the close time for the event."""
        return self.end_from_now_sec() <= 0

    def is_active(self):
        """True if between open and close time for the event."""
        return self.is_started() and not self.is_finished()

    def is_pending(self):
        """True if event has not started."""
        return not self.is_started()

    def is_available(self):
        """True if event has not finished."""
        return not self.is_finished()

    def tostr(self):
        return fmt_time(self.open_datetime) + "," + fmt_time(
            self.close_datetime) + "," + self.group + "," + self.dungeon_name + "," + self.event_type

    def start_pst(self):
        tz = pytz.timezone('US/Pacific')
        return self.open_datetime.astimezone(tz)

    def start_est(self):
        tz = pytz.timezone('US/Eastern')
        return self.open_datetime.astimezone(tz)

    def start_from_now(self):
        return fmt_hrs_mins(self.start_from_now_sec())

    def end_from_now(self):
        return fmt_hrs_mins(self.end_from_now_sec())

    def end_from_now_full_min(self):
        return fmt_days_hrs_mins_short(self.end_from_now_sec())

    def to_guerrilla_str(self):
        return fmt_time_short(self.start_pst())

    def to_date_str(self):
        return self.server + "," + self.group + "," + fmt_time(self.start_pst()) + "," + fmt_time(
            self.start_est()) + "," + self.start_from_now()

    def group_short_name(self):
        return self.group.upper().replace('RED', 'R').replace('BLUE', 'B').replace('GREEN', 'G')

    def group_long_name(self):
        return self.group.upper() if self.group is not None else "UNGROUPED"

    def to_partial_event(self, pe):
        group = self.group_short_name()
        if self.is_started():
            return group + " " + self.end_from_now() + "   " + self.name_and_modifier
        else:
            return group + " " + fmt_time_short(self.start_pst()) + " " + fmt_time_short(
                self.start_est()) + " " + self.start_from_now() + " " + self.name_and_modifier


class EventList:
    def __init__(self, event_list):
        self.event_list = event_list

    def with_func(self, func, exclude=False):
        if exclude:
            return EventList(list(itertools.filterfalse(func, self.event_list)))
        else:
            return EventList(list(filter(func, self.event_list)))

    def with_server(self, server):
        return self.with_func(lambda e: e.server == normalize_server_name(server))

    def with_type(self, event_type):
        return self.with_func(lambda e: e.event_type == event_type)

    def in_type(self, event_types):
        return self.with_func(lambda e: e.event_type in event_types)

    def with_dungeon_type(self, dungeon_type, exclude=False):
        return self.with_func(lambda e: e.technical == dungeon_type, exclude)

    def in_dungeon_type(self, dungeon_types, exclude=False):
        return self.with_func(lambda e: e.technical in dungeon_types, exclude)

    def is_grouped(self, exclude=False):
        return self.with_func(lambda e: e.group is not None, exclude)

    def with_name_contains(self, name, exclude=False):
        return self.with_func(lambda e: name.lower() in e.dungeon_name.lower(), exclude)

    def exclude_unwanted_events(self):
        return self.with_func(is_event_wanted)

    def items(self):
        return self.event_list

    def started_only(self):
        return self.with_func(lambda e: e.is_started())

    def pending_only(self):
        return self.with_func(lambda e: e.is_pending())

    def active_only(self):
        return self.with_func(lambda e: e.is_active())

    def available_only(self):
        return self.with_func(lambda e: e.is_available())

    def items_by_open_time(self, reverse=False):
        return list(sorted(self.event_list, key=(lambda e: (e.open_datetime, e.dungeon_name)), reverse=reverse))

    def items_by_close_time(self, reverse=False):
        return list(sorted(self.event_list, key=(lambda e: (e.close_datetime, e.dungeon_name)), reverse=reverse))


# TIME_FMT = """%a %b %d %H:%M:%S %Y"""


class EventType(Enum):
    Week = 0
    Special = 1
    SpecialWeek = 2
    Guerrilla = 3
    GuerrillaNew = 4
    Etc = -100


class DungeonType(Enum):
    Unknown = -1
    Normal = 0
    CoinDailyOther = 1
    Technical = 2
    Etc = 3
    Unknown4 = 4
    Unknown7 = 7
    Unknown9 = 9


def fmt_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M")


def fmt_time_short(dt):
    return dt.strftime("%H:%M")


def fmt_hrs_mins(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return '{:2}h {:2}m'.format(int(hours), int(minutes))


def fmt_days_hrs_mins_short(sec):
    days, sec = divmod(sec, 86400)
    hours, sec = divmod(sec, 3600)
    minutes, sec = divmod(sec, 60)

    if days > 0:
        return '{:2}d {:2}h'.format(int(days), int(hours))
    elif hours > 0:
        return '{:2}h {:2}m'.format(int(hours), int(minutes))
    else:
        return '{:2}m'.format(int(minutes))


def is_event_wanted(event):
    name = event.name_and_modifier.lower()
    if 'castle of satan' in name:
        # eliminate things like : TAMADRA Invades in [Castle of Satan][Castle of Satan in the Abyss]
        return False

    return True
