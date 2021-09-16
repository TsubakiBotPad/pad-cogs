import asyncio
import datetime
import logging
import re
from collections import defaultdict
from contextlib import suppress
from datetime import timedelta
from enum import Enum
from io import BytesIO
from typing import List, NoReturn, Optional, TYPE_CHECKING, Union

import discord
import itertools
import prettytable
import pytz
import time
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box, humanize_timedelta, inline, pagify
from tsutils.cog_settings import CogSettings
from tsutils.cogs.donations import is_donor
from tsutils.emoji import NO_EMOJI, YES_EMOJI
from tsutils.enums import Server, StarterGroup
from tsutils.errors import ClientInlineTextException
from tsutils.formatting import normalize_server_name, rmdiacritics
from tsutils.helper_classes import DummyObject
from tsutils.helper_functions import repeating_timer
from tsutils.user_interaction import get_user_confirmation, send_cancellation_message, send_confirmation_message

if TYPE_CHECKING:
    from dbcog.models.scheduled_event_model import ScheduledEventModel


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
        self.config.register_global(sent={})
        self.config.register_guild(pingroles={})
        self.config.register_user(dmevents=[])

        # Load event data
        self.events = list()
        self.started_events = set()

        self.fake_uid = -999

        self._event_loop = bot.loop.create_task(self.reload_padevents())
        self._refresh_loop = bot.loop.create_task(self.do_loop())

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
        self._event_loop.cancel()
        self._refresh_loop.cancel()

    async def reload_padevents(self) -> NoReturn:
        await self.bot.wait_until_ready()
        with suppress(asyncio.CancelledError):
            async for _ in repeating_timer(60 * 60):
                try:
                    await self.refresh_data()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Error in loop:")

    async def do_loop(self) -> NoReturn:
        await self.bot.wait_until_ready()
        with suppress(asyncio.CancelledError):
            async for _ in repeating_timer(10):
                try:
                    await self.do_autoevents()
                    await self.do_eventloop()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Error in loop:")

    async def refresh_data(self):
        dbcog = self.bot.get_cog('DBCog')
        await dbcog.wait_until_ready()
        scheduled_events = dbcog.database.get_all_events()

        new_events = []
        for se in scheduled_events:
            try:
                new_events.append(Event(se))
            except Exception as ex:
                logger.exception("Refresh error:")

        self.events = new_events
        self.started_events = {ev.key for ev in new_events if ev.is_started()}
        async with self.config.sent() as seen:
            for key, value in [*seen.items()]:
                if value < time.time() + 60 * 60:
                    del seen[key]

    async def do_autoevents(self):
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
                            or (key, event.key, gid) in await self.config.sent():
                        continue
                    elif aep['regex']:
                        matches = re.search(aep['searchstr'], event.clean_dungeon_name)
                    else:
                        matches = aep['searchstr'].lower() in event.clean_dungeon_name.lower()

                    async with self.config.sent() as sent:
                        sent[(key, event.key, gid)] = time.time()
                    if not matches:
                        continue

                    index = GROUPS.index(event.group)
                    channel = guild.get_channel(aep['channels'][index])
                    if channel is None:
                        continue
                    role = guild.get_role(aep['roles'][index])
                    ment = role.mention if role else ""
                    offsetstr = "now"
                    if aep['offset']:
                        offsetstr = f"<t:{int(event.open_datetime.timestamp())}:R>"
                    try:
                        timestr = humanize_timedelta(timedelta=event.close_datetime - event.open_datetime)
                        await channel.send(f"{event.name_and_modifier} starts {offsetstr}!"
                                           f" It will be active for {timestr}.  {ment}",
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
                            or (aed['key'], event.key, uid) in await self.config.sent():
                        continue
                    if aed.get('include3p') is None:
                        # case of legacy configs
                        aed['include3p'] = True
                    if not aed['include3p'] and event.clean_dungeon_name.startswith("Multiplayer"):
                        continue
                    async with self.config.sent() as sent:
                        sent[(aed['key'], event.key, uid)] = time.time()
                    if aed['searchstr'].lower() in event.clean_dungeon_name.lower():
                        offsetstr = "now"
                        if aed['offset']:
                            offsetstr = f"<t:{int(event.open_datetime.timestamp())}:R>"
                        timestr = humanize_timedelta(timedelta=event.close_datetime - event.open_datetime)
                        try:
                            await user.send(f"{event.clean_dungeon_name} starts {offsetstr}!"
                                            f" It will be active for {timestr}.")
                        except Exception:
                            logger.exception("Failed to send AED to user {}".format(user.id))

    async def do_eventloop(self):
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
                                message = "{}`: {} is starting`".format(role.mention, event.name_and_modifier)
                            else:
                                message = box(f"Server {event.server}, group {event.group_long_name()}:"
                                              f" {event.name_and_modifier}")

                            await channel.send(message, allowed_mentions=discord.AllowedMentions(roles=True))
                        except Exception as ex:
                            # self.settings.remove_guerrilla_reg(gr['channel_id'], gr['server'])
                            logger.exception("caught exception while sending guerrilla msg:")

            else:
                if event.dungeon_type not in [DungeonType.Normal]:
                    msg = self.make_active_text(event.server)
                    for daily_registration in list(self.settings.list_daily_reg()):
                        try:
                            if event.server == daily_registration['server']:
                                await self.page_output(self.bot.get_channel(daily_registration['channel_id']),
                                                       msg, channel_id=daily_registration['channel_id'])
                                logger.info("daily_reg server")
                        except Exception as ex:
                            logger.exception("caught exception while sending daily msg:")

    @commands.group(aliases=['pde'])
    @checks.mod_or_permissions(manage_guild=True)
    async def padevents(self, ctx):
        """PAD event tracking"""

    @padevents.command()
    @checks.is_owner()
    async def testevent(self, ctx, server: Server, seconds: int = 0):
        server = server.value

        dbcog = self.bot.get_cog('DBCog')
        await dbcog.wait_until_ready()
        # TODO: Don't use this awful importing hack
        dg_module = __import__('.'.join(dbcog.__module__.split('.')[:-1]) + ".models.scheduled_event_model")
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
        self.events.append(Event(te))
        await ctx.tick()

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addchannel(self, ctx, server: Server):
        server = server.value

        channel_id = ctx.channel.id
        if self.settings.check_guerrilla_reg(channel_id, server):
            await ctx.send("Channel already active.")
            return

        self.settings.add_guerrilla_reg(channel_id, server)
        await ctx.send("Channel now active.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmchannel(self, ctx, server: Server):
        server = server.value

        channel_id = ctx.channel.id
        if not self.settings.check_guerrilla_reg(channel_id, server):
            await ctx.send("Channel is not active.")
            return

        self.settings.remove_guerrilla_reg(channel_id, server)
        await ctx.send("Channel deactivated.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addchanneldaily(self, ctx, server: Server):
        server = server.value

        channel_id = ctx.channel.id
        if self.settings.check_daily_reg(channel_id, server):
            await ctx.send("Channel already active.")
            return

        self.settings.add_daily_reg(channel_id, server)
        await ctx.send("Channel now active.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmchanneldaily(self, ctx, server: Server):
        server = server.value

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

    @autoeventping.command(name="add", ignore_extra=False)
    async def aep_add(self, ctx, key, server: Server = None, searchstr=None,
                      red_role: Optional[discord.Role] = None,
                      blue_role: Optional[discord.Role] = None,
                      green_role: Optional[discord.Role] = None,
                      channel: discord.TextChannel = None):
        """Add a new autoeventping.
         Use `[p]aep set` with your chosen key to finish or update config.
         `channel` defaults to the current channel.

        Usage:
        `[p]aep add diamondra`
        `[p]aep add pluspoints NA "star treasure" @red @blue @green #channel`
        `[p]aep add wallace KR "wallace" @eventping #channel`
        """

        if " " in key:
            await ctx.send("Multi-word keys are not allowed.")
            return

        if server:
            server = server.value

        if blue_role is None:
            blue_role = green_role = red_role

        default = {
            'roles': [None, None, None],
            'channels': [(channel or ctx.channel).id] * 3,
            'server': server or 'NA',
            'searchstr': searchstr and rmdiacritics(searchstr),
            'regex': False,
            'enabled': bool(red_role or channel),
            'offset': 0,
        }

        if red_role is not None:
            default['roles'] = [red_role.id, blue_role.id, green_role and green_role.id]

        async with self.config.guild(ctx.guild).pingroles() as pingroles:
            pingroles[key] = default

        await ctx.send("New AEP created:")
        await self.aep_show(ctx, key)

    @autoeventping.command(name="remove", aliases=['rm', 'delete'])
    async def aep_remove(self, ctx, key):
        """Remove an autoeventping"""
        async with self.config.guild(ctx.guild).pingroles() as pingroles:
            if key not in pingroles:
                await ctx.send("That key does not exist.")
                return
            del pingroles[key]
        await ctx.tick()

    @autoeventping.command(name="show")
    async def aep_show(self, ctx, key):
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
        pr = (f"Key: `{key}`\n"
              f"\tStatus: {YES_EMOJI + ' enabled' if pingroles[key]['enabled'] else NO_EMOJI + ' disabled'}\n"
              f"\tSearch string: `{pingroles[key]['searchstr']}` {'(regex search)' * pingroles[key]['regex']}\n"
              f"\tServer: {pingroles[key]['server']}\n"
              f"\tRed: {roles[0]} (In {chans[0]})\n"
              f"\tBlue: {roles[1]} (In {chans[1]})\n"
              f"\tGreen: {roles[2]} (In {chans[2]})\n"
              f"\tOffset: `{pingroles[key]['offset']} minutes`")
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

    async def aepchange(self, ctx, key, k, f):
        async with self.config.guild(ctx.guild).pingroles() as pingroles:
            if key not in pingroles:
                await ctx.send("That key does not exist.")
                return
            pingroles[key][k] = f(pingroles[key][k])

    async def aepset(self, ctx, key, k, v):
        await self.aepchange(ctx, key, k, lambda x: v)

    async def aepget(self, ctx, key):
        pingroles = await self.config.guild(ctx.guild).pingroles()
        if key not in pingroles:
            raise ClientInlineTextException(f"Key `{key}` does not exist.  Available keys are:"
                                            f" {', '.join(map(inline, pingroles))}")
        return pingroles[key]

    async def aep_remove_channel(self, ctx, key, group, f):
        pingroles = await self.config.guild(ctx.guild).pingroles()
        if key not in pingroles:
            raise ClientInlineTextException(f"Key `{key}` does not exist.  Available keys are:"
                                            f" {', '.join(map(inline, pingroles))}")

        if not await get_user_confirmation(ctx, "Are you sure you want to remove the {} channel for AEP `{}`?"
                .format(group, key)):
            await send_cancellation_message(ctx,
                                            "No action was taken. You can set a channel with `{}aep set {}channel {} #channel_name`"
                                            .format(ctx.prefix, group, key))
            return
        else:
            await self.aepchange(ctx, key, 'channels', f)
            await send_confirmation_message(ctx, "Okay, I removed the {} channel for the AEP `{}`"
                                            .format(group, key))
            return

    @aep_set.command(name="channel")
    async def aep_s_channel(self, ctx, key, channel: discord.TextChannel):
        """Sets channel to ping for all groups"""
        await self.aepset(ctx, key, 'channels', [channel.id] * 3)
        await ctx.tick()

    @aep_set.command(name="redchannel")
    async def aep_s_redchannel(self, ctx, key, channel: discord.TextChannel = None):
        """Sets channel to ping when event is red"""
        if channel is None:
            await self.aep_remove_channel(ctx, key, "red", lambda x: [None, x[1], x[2]])
        else:
            await self.aepchange(ctx, key, 'channels', lambda x: [channel.id, x[1], x[2]])
            await ctx.tick()

    @aep_set.command(name="bluechannel")
    async def aep_s_bluechannel(self, ctx, key, channel: discord.TextChannel = None):
        """Sets channel to ping when event is blue"""
        if channel is None:
            await self.aep_remove_channel(ctx, key, "blue", lambda x: [x[0], None, x[2]])
        else:
            await self.aepchange(ctx, key, 'channels', lambda x: [x[0], channel.id, x[2]])
            await ctx.tick()

    @aep_set.command(name="greenchannel")
    async def aep_s_greenchannel(self, ctx, key, channel: discord.TextChannel = None):
        """Sets channel to ping when event is green"""
        if channel is None:
            await self.aep_remove_channel(ctx, key, "green", lambda x: [x[0], x[1], None])
        else:
            await self.aepchange(ctx, key, 'channels', lambda x: [x[0], x[1], channel.id])
            await ctx.tick()

    @aep_set.command(name="roles")
    async def aep_s_roles(self, ctx, key, red: discord.Role, blue: discord.Role, green: discord.Role):
        """Sets roles to ping"""
        await self.aepset(ctx, key, 'roles', [red.id, blue.id, green.id])
        await ctx.tick()

    @aep_set.command(name="redrole")
    async def aep_s_redrole(self, ctx, key, role: discord.Role):
        """Sets role to ping when event is red"""
        await self.aepchange(ctx, key, 'roles', lambda x: [role.id, x[1], x[2]])
        await ctx.tick()

    @aep_set.command(name="bluerole")
    async def aep_s_bluerole(self, ctx, key, role: discord.Role):
        """Sets role to ping when event is blue"""
        await self.aepchange(ctx, key, 'roles', lambda x: [x[0], role.id, x[2]])
        await ctx.tick()

    @aep_set.command(name="greenrole")
    async def aep_s_greenrole(self, ctx, key, role: discord.Role):
        """Sets role to ping when event is green"""
        await self.aepchange(ctx, key, 'roles', lambda x: [x[0], x[1], role.id])
        await ctx.tick()

    @aep_set.command(name="server")
    async def aep_s_server(self, ctx, key, server: Server):
        """Sets which server to listen to events in"""
        server = server.value
        await self.aepset(ctx, key, 'server', server)
        await ctx.tick()

    @aep_set.command(name="searchstr")
    async def aep_s_searchstr(self, ctx, key, *, searchstr):
        """Sets what string is tested against event name"""
        searchstr = rmdiacritics(searchstr).strip('"')
        if (await self.aepget(ctx, key))['regex']:
            try:
                re.compile(searchstr)
            except re.error:
                await ctx.send("Invalid regex searchstr. (`{}`)".format(searchstr))
                return
        await self.aepset(ctx, key, 'searchstr', searchstr)
        await ctx.tick()

    @aep_set.command(name="regex")
    async def aep_s_regex(self, ctx, key, regex: bool):
        """Sets whether searchstr is calculated via regex"""
        if regex:
            try:
                re.compile((await self.aepget(ctx, key))['searchstr'])
            except re.error:
                await ctx.send("Invalid regex searchstr. (`{}`)".format((await self.aepget(ctx, key))['searchstr']))
                return
        await self.aepset(ctx, key, 'regex', regex)
        await ctx.tick()

    @aep_set.command(name="enabled", aliases=['enable'])
    async def aep_s_enabled(self, ctx, key, enabled: bool = True):
        """Sets whether or not ping is enabled"""
        await self.aepset(ctx, key, 'enabled', enabled)
        await ctx.tick()

    @aep_set.command(name="disabled", aliases=['disable'])
    async def aep_s_disabled(self, ctx, key, disabled: bool = True):
        """Sets whether or not ping is disabled"""
        await self.aepset(ctx, key, 'enabled', not disabled)
        await ctx.tick()

    @aep_set.command(name="offset")
    async def aep_s_offset(self, ctx, key, offset: int):
        """Sets how many minutes before event should ping happen"""
        if offset < 0:
            await ctx.send("Offset cannot be negative.")
            return
        await self.aepset(ctx, key, 'offset', offset)
        await ctx.tick()

    @commands.group(aliases=['aed'])
    async def autoeventdm(self, ctx):
        """Auto Event DMs"""

    @autoeventdm.command(name="add")
    async def aed_add(self, ctx, server: Server, searchstr, group: Optional[StarterGroup] = None, time_offset: int = 0):
        """Add a new autoeventdm"""
        server = server.value

        if group is None:
            group = 'red'
        else:
            group = GROUPS[group.value]

        if time_offset and not user_is_donor(ctx):
            await ctx.send("You must be a donor to set a time offset!")
            return
        if time_offset < 0:
            await ctx.send("Offset cannot be negative")
            return

        default = {
            'key': time.time(),
            'server': server,
            'group': group,
            'searchstr': searchstr,
            'include3p': True,
            'offset': time_offset,
        }

        index = await self._do_aed_add(ctx, default)
        await ctx.send("New AED created:")
        await self.aed_show(ctx, index)

    @autoeventdm.command(name="remove", aliases=['rm', 'delete'])
    async def aed_remove(self, ctx, index):
        """Remove an autoeventdm"""
        corrected_index = await self._get_and_validate_aed_index(ctx, index)
        if corrected_index is None:
            return
        async with self.config.user(ctx.author).dmevents() as dmevents:
            if not await get_user_confirmation(ctx, "Are you sure you want to delete autoeventdm {}. `{}`?"
                    .format(corrected_index + 1, dmevents[corrected_index]['searchstr'])):
                return
            dmevents.pop(corrected_index)
        await ctx.tick()

    @autoeventdm.command(name="show")
    async def aed_show(self, ctx, index):
        """Show specifics of an autoeventdm"""
        dmevents = await self.config.user(ctx.author).dmevents()
        corrected_index = await self._get_and_validate_aed_index(ctx, index)
        if corrected_index is None:
            return
        if dmevents[corrected_index].get('include3p') is None:
            # case of legacy configs
            dmevents[corrected_index]['include3p'] = True
        ret = (f"Lookup number: `{corrected_index + 1}`\n"
               f"\tSearch string: `{dmevents[corrected_index]['searchstr']}`\n"
               f"\t3P: {'included' if dmevents[corrected_index]['include3p'] else 'excluded'}\n"
               f"\tServer: {dmevents[corrected_index]['server']}\n"
               f"\tGroup: {dmevents[corrected_index]['group'].title()} \n"
               f"\tOffset (Donor Only): `{dmevents[corrected_index]['offset']} minutes`")
        await ctx.send(ret)

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
        if not await get_user_confirmation(ctx, "Are you sure you want to purge your autoeventdms?"):
            return
        await self.config.user(ctx.author).dmevents.set([])
        await ctx.tick()

    @autoeventdm.group(name="edit", aliases=["set"])
    async def aed_e(self, ctx):
        """Edit a property of the autoeventdm"""

    async def _do_aed_add(self, ctx, item):
        """Add autoeventdm and return its index"""
        async with self.config.user(ctx.author).dmevents() as dmevents:
            dmevents.append(item)
        return len(dmevents)

    @is_donor()
    @aed_e.command(name="offset")
    async def aed_e_offset(self, ctx, index, offset: int):
        """(DONOR ONLY) Set time offset to an AED to allow you to prepare for a dungeon"""
        if offset < 0:
            await send_cancellation_message(ctx, "Offset cannot be negative")
            return
        corrected_index = await self._get_and_validate_aed_index(ctx, index)
        if corrected_index is None:
            return
        async with self.config.user(ctx.author).dmevents() as dmevents:
            if not await get_user_confirmation(ctx, "Modify the offset for {}. `{}` to {} minutes?"
                    .format(corrected_index + 1, dmevents[corrected_index]['searchstr'], offset)):
                return
            dmevents[corrected_index]['offset'] = offset
        await ctx.tick()

    @aed_e.command(name="searchstr")
    async def aed_e_searchstr(self, ctx, index, *, searchstr):
        """Set search string of an autoeventdm"""
        searchstr = searchstr.strip('"')
        corrected_index = await self._get_and_validate_aed_index(ctx, index)
        if corrected_index is None:
            return
        async with self.config.user(ctx.author).dmevents() as dmevents:
            if not await get_user_confirmation(ctx, "Modify the search string for {}. `{}` to `{}`?"
                    .format(corrected_index + 1, dmevents[corrected_index]['searchstr'], searchstr)):
                return
            dmevents[corrected_index]['searchstr'] = searchstr
        await ctx.tick()

    @aed_e.command(name="toggle3p")
    async def aed_e_toggle3p(self, ctx, index):
        """Include/exclude 3-player dungeons in an autoeventdm"""
        corrected_index = await self._get_and_validate_aed_index(ctx, index)
        if corrected_index is None:
            return
        async with self.config.user(ctx.author).dmevents() as dmevents:
            event = dmevents[corrected_index]['searchstr']
            if dmevents[corrected_index].get('include3p') is None:
                # case of legacy configs
                dmevents[corrected_index]['include3p'] = True
            if dmevents[corrected_index]['include3p']:
                dmevents[corrected_index]['include3p'] = False
                await send_confirmation_message(ctx, "I will **exclude** 3P dungeons for {}. `{}`"
                                                .format(corrected_index + 1, event))
                return
            dmevents[corrected_index]['include3p'] = True
            await send_confirmation_message(ctx, "I will **include** 3P dungeons for {}. `{}`"
                                            .format(corrected_index + 1, event))
            return

    async def _get_and_validate_aed_index(self, ctx, user_index: Union[str, int]):
        """Returns the corrected index for the autoeventdm of interest, based on Python list indexing"""
        async with self.config.user(ctx.author).dmevents() as dmevents:
            if isinstance(user_index, int) or user_index.isdigit():
                user_index = int(user_index)
                if not 0 < user_index <= len(dmevents):
                    await send_cancellation_message(ctx, "That isn't a valid numerical index.")
                    return None
            else:
                str_index = None
                for i in range(1, len(dmevents) + 1, 1):
                    if dmevents[i - 1]['searchstr'] == user_index:
                        str_index = i
                        break
                user_index = str_index
                if user_index is None:
                    await send_cancellation_message(ctx, "That string did not match any existing patterns. "
                                                         "Printing all of your Auto Event DMs (you can also see this with `{}aed list`):"
                                                    .format(ctx.prefix))
                    await self.aed_list(ctx)
                    return None
        return user_index - 1

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
    async def active(self, ctx, server: Server):
        server = server.value

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
    async def eventsna(self, ctx, group: StarterGroup = None):
        """Display upcoming daily events for NA."""
        await self.do_partial(ctx, Server.NA, group)

    @commands.command()
    async def eventsjp(self, ctx, group: StarterGroup = None):
        """Display upcoming daily events for JP."""
        await self.do_partial(ctx, Server.JP, group)

    @commands.command()
    async def eventskr(self, ctx, group: StarterGroup = None):
        """Display upcoming daily events for KR."""
        await self.do_partial(ctx, Server.KR, group)

    async def do_partial(self, ctx, server: Server, group: StarterGroup = None):
        server = server.value

        if group is not None:
            group = GROUPS[group.value]

        events = EventList(self.events)
        events = events.with_server(server)
        events = events.in_dungeon_type([DungeonType.Etc, DungeonType.CoinDailyOther])
        events = events.is_grouped()

        active_events = events.active_only().items_by_open_time(reverse=True)
        pending_events = events.pending_only().items_by_open_time(reverse=True)

        if group is not None:
            active_events = [e for e in active_events if e.group == group.lower()]
            pending_events = [e for e in pending_events if e.group == group.lower()]

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
    def __init__(self, scheduled_event: "ScheduledEventModel"):
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

        self.event_type_id = scheduled_event.event_type_id
        self.event_type = None

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
        self.event_list: List[Event] = event_list

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
        return self.with_func(lambda e: e.dungeon_type == dungeon_type, exclude)

    def in_dungeon_type(self, dungeon_types, exclude=False):
        return self.with_func(lambda e: e.dungeon_type in dungeon_types, exclude)

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
    Unknown10 = 10


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
