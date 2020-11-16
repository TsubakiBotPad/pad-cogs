import asyncio
import datetime
import discord
import logging
import itertools
import prettytable
import pytz
import re
import traceback
from io import BytesIO
from collections import defaultdict
from datetime import timedelta
from enum import Enum
from redbot.core import checks
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import box, inline, pagify
from tsutils import CogSettings, confirm_message

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dadguide.database_context import DbContext
    from dadguide.models.scheduled_event_model import ScheduledEventModel

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
                events = filter(lambda e: not e.key in self.started_events, self.events)
                for e in events:
                    for gid, data in (await self.config.all_guilds()).items():
                        guild = self.bot.get_guild(gid)
                        if guild is None: continue
                        for key, aep in data.get('pingroles', {}).items():
                            if e.start_from_now_sec() > aep['offset'] * 60 \
                                        or not aep['enabled'] \
                                        or e.server != aep['server'] \
                                        or (key, e.key) in self.rolepinged_events:
                                continue
                            elif aep['regex']:
                                matches = re.search(aep['searchstr'], e.clean_dungeon_name)
                            else:
                                matches = aep['searchstr'] in e.clean_dungeon_name

                            self.rolepinged_events.add((key, e.key))
                            if matches:
                                index = GROUPS.index(e.group)
                                channel = guild.get_channel(aep['channels'][index])
                                if channel is not None:
                                    role = guild.get_role(aep['roles'][index])
                                    ment = role.mention if role else ""
                                    offsetstr = ""
                                    if aep['offset']:
                                        offsetstr = " in {} minute(s)".format(aep['offset'])
                                    try:
                                        await channel.send("{}{} {}".format(e.name_and_modifier, offsetstr, ment), allowed_mentions=discord.AllowedMentions(roles=True))
                                    except Exception:
                                        logger.exception("Failed to send AEP in channel {}".format(channel.id))

                    for uid, data in (await self.config.all_users()).items():
                        user = self.bot.get_user(uid)
                        if user is None: continue
                        for aed in data.get('dmevents', []):
                            if e.start_from_now_sec() > aed['offset'] * 60 \
                                        or e.group != aed['group'] \
                                        or e.server != aed['server'] \
                                        or (aed['key'], e.key) in self.rolepinged_events:
                                continue
                            self.rolepinged_events.add((aed['key'], e.key))
                            if aed['searchstr'] in e.clean_dungeon_name:
                                offsetstr = " starts now!"
                                if aed['offset']:
                                    offsetstr = " starts in {} minute(s)!".format(aed['offset'])
                                try:
                                    await user.send(e.clean_dungeon_name + offsetstr)
                                except Exception:
                                    logger.exception("Failed to send AED to user {}".format(user.id))

                events = filter(lambda e: e.is_started() and not e.key in self.started_events, self.events)
                daily_refresh_servers = set()
                for e in events:
                    self.started_events.add(e.key)
                    if e.event_type in [EventType.Guerrilla, EventType.GuerrillaNew, EventType.SpecialWeek, EventType.Week]:
                        for gr in list(self.settings.listGuerrillaReg()):
                            if e.server == gr['server']:
                                try:
                                    channel = self.bot.get_channel(int(gr['channel_id']))

                                    role_name = '{}_group_{}'.format(e.server, e.groupLongName())
                                    role = channel.guild.get_role(role_name)
                                    if role and role.mentionable:
                                        message = "{} `: {} is starting`".format(role.mention, e.name_and_modifier)
                                    else:
                                        message = box("Server " + e.server + ", group " + e.groupLongName() + " : " + e.name_and_modifier)

                                    await channel.send(message, allowed_mentions=discord.AllowedMentions(roles=True))
                                except Exception as ex:
                                    # self.settings.removeGuerrillaReg(gr['channel_id'], gr['server'])
                                    logger.exception("caught exception while sending guerrilla msg:")

                    else:
                        if not e.dungeon_type in [DungeonType.Normal]:
                            msg = self.makeActiveText(server)
                            for daily_registration in list(self.settings.listDailyReg()):
                                try:
                                    if server == daily_registration['server']:
                                        await self.pageOutput(self.bot.get_channel(daily_registration['channel_id']),
                                                              msg, channel_id=daily_registration['channel_id'])
                                        logger.info("daily_reg server")
                                except Exception as ex:
                                    # self.settings.removeDailyReg(
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
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        dg_cog = self.bot.get_cog('Dadguide')
        await dg_cog.wait_until_ready()
        dg_module = __import__(dg_cog.__module__)

        te = dg_module.ScheduledEventModule({'dungeon_id': 1})

        te.server = server
        te.server_id = SUPPORTED_SERVERS.index(server)
        te.event_type_id = EventType.Guerrilla.value
        te.event_seq = 0
        fuid = self.fake_uid = self.fake_uid - 1
        te.key = lambda: fuid
        te.group_name = 'red'

        te.open_datetime = datetime.datetime.now(pytz.utc) + timedelta(seconds=seconds)
        te.close_datetime = te.open_datetime + timedelta(minutes=1)

        class Dungeon: pass
        d = Dungeon()
        d.name_en = 'fake_dungeon_name'
        d.dungeon_type = DungeonType.Unknown7
        te.event_modifier = 'fake_event_modifier'
        self.events.append(Event(te, self.bot.get_cog('Dadguide').database))

        await ctx.send("Fake event injected.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addchannel(self, ctx, server):
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        channel_id = ctx.channel.id
        if self.settings.checkGuerrillaReg(channel_id, server):
            await ctx.send("Channel already active.")
            return

        self.settings.addGuerrillaReg(channel_id, server)
        await ctx.send("Channel now active.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmchannel(self, ctx, server):
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        channel_id = ctx.channel.id
        if not self.settings.checkGuerrillaReg(channel_id, server):
            await ctx.send("Channel is not active.")
            return

        self.settings.removeGuerrillaReg(channel_id, server)
        await ctx.send("Channel deactivated.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addchanneldaily(self, ctx, server):
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        channel_id = ctx.channel.id
        if self.settings.checkDailyReg(channel_id, server):
            await ctx.send("Channel already active.")
            return

        self.settings.addDailyReg(channel_id, server)
        await ctx.send("Channel now active.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmchanneldaily(self, ctx, server):
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        channel_id = ctx.channel.id
        if not self.settings.checkDailyReg(channel_id, server):
            await ctx.send("Channel is not active.")
            return

        self.settings.removeDailyReg(channel_id, server)
        await ctx.send("Channel deactivated.")

    @commands.group(aliases=['aep'])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def autoeventping(self, ctx):
        """Auto Event Pings"""

    @autoeventping.command(name="add")
    async def aep_add(self, ctx, key, server = None, searchstr = None, red: discord.Role = None, blue: discord.Role = None, green: discord.Role = None):
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
            server = normalizeServer(server)
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
              f"    Search String: '{pingroles[key]['searchstr']}' {'(regex search)' if pingroles[key]['regex'] else ''}\n"
              f"    Server: {pingroles[key]['server']}\n"
              f"    Red: {roles[0]} (In {chans[0]})\n"
              f"    Blue: {roles[1]} (In {chans[1]})\n"
              f"    Green: {roles[2]} (In {chans[2]})\n"
              f"    Offset: {pingroles[key]['offset']} minutes")
        await ctx.send(pr)

    @autoeventping.command(name="list")
    async def aep_list(self, ctx):
        """List all autoeventpings"""
        pingroles = await self.config.guild(ctx.guild).pingroles()
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
        await self.aeps(ctx, key, 'channels', [channel.id]*3)
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
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return
        await self.aeps(ctx, key, 'server', server)
        await ctx.tick()

    @aep_set.command(name="searchstr")
    async def aep_s_searchstr(self, ctx, key, *, searchstr):
        """Sets what string is tested against event name"""
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
    async def aed_add(self, ctx, server, searchstr, group, offset: int = 0):
        """Add a new autoeventdm"""
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return
        group = group.lower()
        if group not in GROUPS:
            await ctx.send("Unsupported group, pick one of red, blue, green")
            return
        if offset < 0:
            await ctx.send("Offset cannot be negative")
            return
        elif offset > 0:
            DONOR_COG = self.bot.get_cog("Donations")
            if DONOR_COG is None:
                await ctx.send(inline("Donor Cog not loaded.  Please contact a bot admin."))
            elif not DONOR_COG.is_donor(ctx):
                await ctx.send(("AED offset is a donor only feature due to server loads."
                                " Your auto event DM will be created, but the offset will not"
                                " be in affect until you're a donor.  You can donate any time"
                                " at https://www.patreon.com/tsubaki_bot.  Use `{}donate` to"
                                " view this link at any time").format(ctx.prefix))

        default = {
            'key': datetime.datetime.now().timestamp(),
            'server': server,
            'group': group,
            'searchstr': searchstr,
            'offset': offset,
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
                                               "").format(dmevents[index-1]['searchstr'])):
                return
            dmevents.pop(index-1)
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

    @aed_e.command(name="offset")
    async def aed_e_offset(self, ctx, index, offset):
        """Set offset of an autoeventdm (Donor only)"""
        if offset < 0:
            await ctx.send("Offset cannot be negative")
            return
        elif offset > 0:
            DONOR_COG = self.bot.get_cog("Donations")
            if DONOR_COG is None:
                await ctx.send(inline("Donor Cog not loaded.  Please contact a bot admin."))
            elif not DONOR_COG.is_donor(ctx):
                await ctx.send(("AED offset is a donor only feature due to server loads."
                                " Your auto event DM will be created, but the offset will not"
                                " be in affect until you're a donor.  You can donate any time"
                                " at https://www.patreon.com/tsubaki_bot.  Use `{}donate` to"
                                " view this link at any time").format(ctx.prefix))
        async with self.config.user(ctx.author).dmevents() as dmevents:
            if not 0 < index <= len(dmevents):
                await ctx.send("That isn't a valid index.")
                return
            dmevents[index-1]['offset'] = offset
        await ctx.tick()

    @aed_e.command(name="searchstr")
    async def aed_e_searchstr(self, ctx, index, *, searchstr):
        """Set search string of an autoeventdm"""
        async with self.config.user(ctx.author).dmevents() as dmevents:
            if not 0 < index <= len(dmevents):
                await ctx.send("That isn't a valid index.")
                return
            dmevents[index-1]['searchstr'] = searchstr
        await ctx.tick()

    @padevents.command(name="listallchannels")
    @checks.is_owner()
    async def _listallchannel(self, ctx):
        msg = 'Following daily channels are registered:\n'
        msg += self.makeChannelList(self.settings.listDailyReg())
        msg += "\n"
        msg += 'Following guerilla channels are registered:\n'
        msg += self.makeChannelList(self.settings.listGuerrillaReg())
        await self.pageOutput(ctx, msg)

    @padevents.command(name="listchannels")
    @checks.mod_or_permissions(manage_guild=True)
    async def _listchannel(self, ctx):
        msg = 'Following daily channels are registered:\n'
        msg += self.makeChannelList(self.settings.listDailyReg(), lambda c: c in ctx.guild.channels)
        msg += "\n"
        msg += 'Following guerilla channels are registered:\n'
        msg += self.makeChannelList(self.settings.listGuerrillaReg(), lambda c: c in ctx.guild.channels)
        await self.pageOutput(ctx, msg)

    def makeChannelList(self, reg_list, filt=None):
        if filt is None:
            filt = lambda x: x
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
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        msg = self.makeActiveText(server)
        await self.pageOutput(ctx, msg)

    def makeActiveText(self, server):
        server_events = EventList(self.events).withServer(server)
        active_events = server_events.activeOnly()
        pending_events = server_events.pendingOnly()
        available_events = server_events.availableOnly()

        msg = "Listing all events for " + server

        """
        special_events = active_events.withType(
            EventType.Special).itemsByCloseTime()
        if len(special_events) > 0:
            msg += "\n\n" + self.makeActiveOutput('Special Events', special_events)

        all_etc_events = active_events.withType(EventType.Etc)

        etc_events = all_etc_events.withDungeonType(
            DungeonType.Etc).excludeUnwantedEvents().itemsByCloseTime()
        if len(etc_events) > 0:
            msg += "\n\n" + self.makeActiveOutput('Etc Events', etc_events)

        # Old-style guerrillas
        active_guerrilla_events = active_events.withType(EventType.Guerrilla).items()
        if len(active_guerrilla_events) > 0:
            msg += "\n\n" + \
                   self.makeActiveGuerrillaOutput('Active Guerrillas', active_guerrilla_events)

        guerrilla_events = pending_events.withType(EventType.Guerrilla).items()
        if len(guerrilla_events) > 0:
            msg += "\n\n" + self.makeFullGuerrillaOutput('Guerrilla Events', guerrilla_events)

        # New-style guerrillas
        active_guerrilla_events = active_events.withType(EventType.SpecialWeek).items()
        if len(active_guerrilla_events) > 0:
            msg += "\n\n" + \
                   self.makeActiveGuerrillaOutput('Active Guerrillas', active_guerrilla_events)

        guerrilla_events = pending_events.withType(EventType.SpecialWeek).items()
        if len(guerrilla_events) > 0:
            msg += "\n\n" + \
                   self.makeFullGuerrillaOutput(
                       'Guerrilla Events', guerrilla_events, starter_guerilla=True)
        """
        active_cdo_events = active_events.withDungeonType(DungeonType.CoinDailyOther).isGrouped(True).items()
        if len(active_cdo_events) > 0:
            msg += "\n\n" + \
                   self.makeActiveOutput(
                       'Active Events', active_cdo_events)
        """
        cdo_events = pending_events.withDungeonType(DungeonType.CoinDailyOther).isGrouped(False).items()
        if len(cdo_events) > 0:
            msg += "\n\n" + \
                   self.makeActiveOutput(
                       'Reward Events', cdo_events)
        """

        active_grouped_cdo_events = active_events.withDungeonType(DungeonType.CoinDailyOther).isGrouped().items()
        if len(active_grouped_cdo_events) > 0:
            msg += "\n\n" + \
                   self.makeActiveGuerrillaOutput(
                       'Active Guerrillas', active_grouped_cdo_events)
        grouped_cdo_events = pending_events.withDungeonType(DungeonType.CoinDailyOther).isGrouped().items()
        if len(grouped_cdo_events) > 0:
            msg += "\n\n" + \
                   self.makeFullGuerrillaOutput(
                       'Guerrillas', grouped_cdo_events, starter_guerilla=True)

        active_etc_events = active_events.withDungeonType(DungeonType.Etc).items()
        if len(active_etc_events) > 0:
            msg += "\n\n" + \
                   self.makeActiveOutput(
                       'Active Other Events', active_etc_events)
        """
        etc_events = pending_events.withDungeonType(DungeonType.Etc).items()
        if len(etc_events) > 0:
            msg += "\n\n" + \
                   self.makeActiveOutput(
                       'Other Events', etc_events)
        """
        # clean up long headers
        msg = msg.replace('-------------------------------------', '-----------------------')

        return msg

    async def pageOutput(self, ctx, msg, channel_id=None, format_type=box):
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

    def makeActiveOutput(self, table_name, event_list):
        tbl = prettytable.PrettyTable(["Time", table_name])
        tbl.hrules = prettytable.HEADER
        tbl.vrules = prettytable.NONE
        tbl.align[table_name] = "l"
        tbl.align["Time"] = "r"
        for e in event_list:
            tbl.add_row([e.endFromNowFullMin().strip(), e.name_and_modifier])
        return tbl.get_string()

    def makeActiveGuerrillaOutput(self, table_name, event_list):
        tbl = prettytable.PrettyTable([table_name, "Group", "Time"])
        tbl.hrules = prettytable.HEADER
        tbl.vrules = prettytable.NONE
        tbl.align[table_name] = "l"
        tbl.align["Time"] = "r"
        for e in event_list:
            tbl.add_row([e.name_and_modifier, e.group, e.endFromNowFullMin().strip()])
        return tbl.get_string()

    def makeFullGuerrillaOutput(self, table_name, event_list, starter_guerilla=False):
        events_by_name = defaultdict(list)
        for e in event_list:
            events_by_name[e.name_and_modifier].append(e)

        rows = list()
        grps = ["RED", "BLUE", "GREEN"] if starter_guerilla else ["A", "B", "C", "D", "E"]
        for name, events in events_by_name.items():
            events = sorted(events, key=lambda e: e.open_datetime)
            events_by_group = defaultdict(list)
            for e in events:
                events_by_group[e.group.upper()].append(e)

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
                        e = grp_list.pop(0)
                        row.append(e.toGuerrillaStr())
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
        await self.doPartial(ctx, 'NA')

    @commands.command()
    async def eventsjp(self, ctx):
        """Display upcoming daily events for JP."""
        await self.doPartial(ctx, 'JP')

    @commands.command()
    async def eventskr(self, ctx):
        """Display upcoming daily events for KR."""
        await self.doPartial(ctx, 'KR')

    async def doPartial(self, ctx, server):
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        events = EventList(self.events)
        events = events.withServer(server)
        events = events.inDungeonType([DungeonType.Etc, DungeonType.CoinDailyOther])
        events = events.isGrouped()

        active_events = events.activeOnly().itemsByOpenTime(reverse=True)
        pending_events = events.pendingOnly().itemsByOpenTime(reverse=True)

        group_to_active_event = {e.group: e for e in active_events}
        group_to_pending_event = {e.group: e for e in pending_events}

        #active_events = list(group_to_active_event.values())
        #pending_events = list(group_to_pending_event.values())

        active_events.sort(key=lambda e: (GROUPS.index(e.group), e.open_datetime))
        pending_events.sort(key=lambda e: (GROUPS.index(e.group), e.open_datetime))

        if len(active_events) == 0 and len(pending_events) == 0:
            await ctx.send("No events available for " + server)
            return

        output = "Events for {}".format(server)

        if len(active_events) > 0:
            output += "\n\n" + "  Remaining Dungeon"
            for e in active_events:
                output += "\n" + e.toPartialEvent(self)

        if len(pending_events) > 0:
            output += "\n\n" + "  PT    ET    ETA     Dungeon"
            for e in pending_events:
                output += "\n" + e.toPartialEvent(self)

        for page in pagify(output):
            await ctx.send(box(page))


def makeChannelReg(channel_id, server):
    server = normalizeServer(server)
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

    def listGuerrillaReg(self):
        return self.bot_settings['guerrilla_regs']

    def addGuerrillaReg(self, channel_id, server):
        self.listGuerrillaReg().append(makeChannelReg(channel_id, server))
        self.save_settings()

    def checkGuerrillaReg(self, channel_id, server):
        return makeChannelReg(channel_id, server) in self.listGuerrillaReg()

    def removeGuerrillaReg(self, channel_id, server):
        if self.checkGuerrillaReg(channel_id, server):
            self.listGuerrillaReg().remove(makeChannelReg(channel_id, server))
            self.save_settings()

    def listDailyReg(self):
        return self.bot_settings['daily_regs']

    def addDailyReg(self, channel_id, server):
        self.listDailyReg().append(makeChannelReg(channel_id, server))
        self.save_settings()

    def checkDailyReg(self, channel_id, server):
        return makeChannelReg(channel_id, server) in self.listDailyReg()

    def removeDailyReg(self, channel_id, server):
        if self.checkDailyReg(channel_id, server):
            self.listDailyReg().remove(makeChannelReg(channel_id, server))
            self.save_settings()


class Event:
    def __init__(self, scheduled_event: "ScheduledEventModel", db_context):
        self.db_context = db_context
        self.key = scheduled_event.key()
        self.server = SUPPORTED_SERVERS[scheduled_event.server_id]
        self.open_datetime = scheduled_event.open_datetime
        self.close_datetime = scheduled_event.close_datetime
        self.group = scheduled_event.group_name
        self.dungeon = scheduled_event.dungeon
        self.dungeon_name = self.dungeon.name_en if self.dungeon else 'unknown_dungeon'
        self.event_name = ''  # scheduled_event.event.name if scheduled_event.event else ''

        self.clean_dungeon_name = cleanDungeonNames(self.dungeon_name)
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
        return fmtTime(self.open_datetime) + "," + fmtTime(
            self.close_datetime) + "," + self.group + "," + self.dungeon_code + "," + self.event_type + "," + self.event_seq

    def startPst(self):
        tz = pytz.timezone('US/Pacific')
        return self.open_datetime.astimezone(tz)

    def startEst(self):
        tz = pytz.timezone('US/Eastern')
        return self.open_datetime.astimezone(tz)

    def startFromNow(self):
        return fmtHrsMins(self.start_from_now_sec())

    def endFromNow(self):
        return fmtHrsMins(self.end_from_now_sec())

    def endFromNowFullMin(self):
        return fmtDaysHrsMinsShort(self.end_from_now_sec())

    def toGuerrillaStr(self):
        return fmtTimeShort(self.startPst())

    def toDateStr(self):
        return self.server + "," + self.group + "," + fmtTime(self.startPst()) + "," + fmtTime(
            self.startEst()) + "," + self.startFromNow()

    def groupShortName(self):
        return self.group.upper().replace('RED', 'R').replace('BLUE', 'B').replace('GREEN', 'G')

    def groupLongName(self):
        return self.group.upper() if self.group is not None else "UNGROUPED"

    def toPartialEvent(self, pe):
        group = self.groupShortName()
        if self.is_started():
            return group + " " + self.endFromNow() + "   " + self.name_and_modifier
        else:
            return group + " " + fmtTimeShort(self.startPst()) + " " + fmtTimeShort(
                self.startEst()) + " " + self.startFromNow() + " " + self.name_and_modifier


class EventList:
    def __init__(self, event_list):
        self.event_list = event_list

    def withFunc(self, func, exclude=False):
        if exclude:
            return EventList(list(itertools.filterfalse(func, self.event_list)))
        else:
            return EventList(list(filter(func, self.event_list)))

    def withServer(self, server):
        return self.withFunc(lambda e: e.server == normalizeServer(server))

    def withType(self, event_type):
        return self.withFunc(lambda e: e.event_type == event_type)

    def inType(self, event_types):
        return self.withFunc(lambda e: e.event_type in event_types)

    def withDungeonType(self, dungeon_type, exclude=False):
        return self.withFunc(lambda e: e.dungeon_type == dungeon_type, exclude)

    def inDungeonType(self, dungeon_types, exclude=False):
        return self.withFunc(lambda e: e.dungeon_type in dungeon_types, exclude)

    def isGrouped(self, exclude=False):
        return self.withFunc(lambda e: e.group is not None, exclude)

    def withNameContains(self, name, exclude=False):
        return self.withFunc(lambda e: name.lower() in e.dungeon_name.lower(), exclude)

    def excludeUnwantedEvents(self):
        return self.withFunc(isEventWanted)

    def items(self):
        return self.event_list

    def startedOnly(self):
        return self.withFunc(lambda e: e.is_started())

    def pendingOnly(self):
        return self.withFunc(lambda e: e.is_pending())

    def activeOnly(self):
        return self.withFunc(lambda e: e.is_active())

    def availableOnly(self):
        return self.withFunc(lambda e: e.is_available())

    def itemsByOpenTime(self, reverse=False):
        return list(sorted(self.event_list, key=(lambda e: (e.open_datetime, e.dungeon_name)), reverse=reverse))

    def itemsByCloseTime(self, reverse=False):
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


def fmtTime(dt):
    return dt.strftime("%Y-%m-%d %H:%M")


def fmtTimeShort(dt):
    return dt.strftime("%H:%M")


def fmtHrsMins(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return '{:2}h {:2}m'.format(int(hours), int(minutes))


def fmtDaysHrsMinsShort(sec):
    days, sec = divmod(sec, 86400)
    hours, sec = divmod(sec, 3600)
    minutes, sec = divmod(sec, 60)

    if days > 0:
        return '{:2}d {:2}h'.format(int(days), int(hours))
    elif hours > 0:
        return '{:2}h {:2}m'.format(int(hours), int(minutes))
    else:
        return '{:2}m'.format(int(minutes))


def normalizeServer(server):
    server = server.upper()
    return 'NA' if server == 'US' else server


def isEventWanted(event):
    name = event.name_and_modifier.lower()
    if 'castle of satan' in name:
        # eliminate things like : TAMADRA Invades in [Castle of Satan][Castle of Satan in the Abyss]
        return False

    return True


def cleanDungeonNames(name):
    # TODO: Make this info internally stored
    if 'tamadra invades in some tech' in name.lower():
        return 'Latents invades some Techs & 20x +Eggs'
    if '1.5x Bonus Pal Point in multiplay' in name:
        name = '[Descends] 1.5x Pal Points in multiplay'
    name = name.replace('No Continues', 'No Cont')
    name = name.replace('No Continue', 'No Cont')
    name = name.replace('Some Limited Time Dungeons', 'Some Guerrillas')
    name = name.replace('are added in', 'in')
    name = name.replace('!', '')
    name = name.replace('Dragon Infestation', 'Dragons')
    name = name.replace(' Infestation', 's')
    name = name.replace('Daily Descended Dungeon', 'Daily Descends')
    name = name.replace('Chance for ', '')
    name = name.replace('Jewel of the Spirit', 'Spirit Jewel')
    name = name.replace(' & ', '/')
    name = name.replace(' / ', '/')
    name = name.replace('PAD Radar', 'PADR')
    name = name.replace('in normal dungeons', 'in normals')
    name = name.replace('Selected ', 'Some ')
    name = name.replace('Enhanced ', 'Enh ')
    name = name.replace('All Att. Req.', 'All Att.')
    name = name.replace('Extreme King Metal Dragon', 'Extreme KMD')
    name = name.replace('Golden Mound-Tricolor [Fr/Wt/Wd Only]', 'Golden Mound')
    name = name.replace('Gods-Awakening Materials Descended', "Awoken Mats")
    name = name.replace('Orb move time 4 sec', '4s move time')
    name = name.replace('Awakening Materials Descended', 'Awkn Mats')
    name = name.replace('Awakening Materials', 'Awkn Mats')
    name = name.replace("Star Treasure Thieves' Den", 'STTD')
    name = name.replace('Ruins of the Star Vault', 'Star Vault')
    name = name.replace('-★6 or lower Enhanced', '')

    return name
