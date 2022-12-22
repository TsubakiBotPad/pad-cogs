import logging
import re
from typing import Any, Dict, Optional, Set, TypeVar, Union

import discord
import time
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, humanize_timedelta, inline
from tsutils.cogs.donations import is_donor
from tsutils.emoji import NO_EMOJI, YES_EMOJI
from tsutils.enums import Server
from tsutils.errors import ClientInlineTextException
from tsutils.formatting import rmdiacritics
from tsutils.user_interaction import get_user_confirmation, send_cancellation_message, send_confirmation_message

from padevents.events import Event

logger = logging.getLogger('red.padbot-cogs.padevents')
T = TypeVar("T")


def user_is_donor(ctx, only_patron=False):
    if ctx.author.id in ctx.bot.owner_ids:
        return True
    donationcog = ctx.bot.get_cog("Donations")
    if not donationcog:
        return False
    return donationcog.is_donor(ctx, only_patron)


class AutoEvent:
    bot: Red
    config: Config
    events: Set[Event]
    started_events: Set[Event]

    async def do_autoevents(self):
        events = filter(lambda e: e.key not in self.started_events, self.events)
        for event in events:
            for gid, data in (await self.config.all_guilds()).items():
                guild = self.bot.get_guild(gid)
                if guild is None:
                    continue
                for key, aep in data.get('pingroles', {}).items():
                    if event.start_from_now_sec() > aep['offset'] * 60 \
                            or str((key, event.key, gid)) in await self.config.sent():
                        continue
                    if not self.event_matches_autoevent(event, aep):
                        continue

                    async with self.config.sent() as sent:
                        sent[str((key, event.key, gid))] = time.time()

                    channel = guild.get_channel(aep['channel'])
                    if channel is None:
                        continue
                    role = guild.get_role(aep['role'])
                    ment = role.mention if role else ""
                    offsetstr = "now"
                    if aep['offset']:
                        offsetstr = f"<t:{int(event.open_datetime.timestamp())}:R>"
                    try:
                        timestr = humanize_timedelta(timedelta=event.close_datetime - event.open_datetime)
                        await channel.send(f"{event.clean_dungeon_name} starts {offsetstr}!"
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
                            or str((aed['key'], event.key, uid)) in await self.config.sent():
                        continue
                    if not self.event_matches_autoevent(event, aed):
                        continue
                    async with self.config.sent() as sent:
                        sent[str((aed['key'], event.key, uid))] = time.time()
                    offsetstr = "now"
                    if aed['offset']:
                        offsetstr = f"<t:{int(event.open_datetime.timestamp())}:R>"
                    timestr = humanize_timedelta(timedelta=event.close_datetime - event.open_datetime)
                    try:
                        await user.send(f"{event.clean_dungeon_name} starts {offsetstr}!"
                                        f" It will be active for {timestr}.")
                    except Exception:
                        logger.exception("Failed to send AED to user {}".format(user.id))

    def event_matches_autoevent(self, event: Event, autoevent: Dict[str, Any]):
        if not autoevent.get('enabled', True) \
                or event.server != autoevent['server'] \
                or autoevent['searchstr'] is None:
            return False
        if not autoevent.get('include3p', True) and event.clean_dungeon_name.startswith("Multiplayer"):
            return False
        if autoevent.get('regex'):
            return re.search(autoevent['searchstr'], event.clean_dungeon_name) \
                   or re.search(autoevent['searchstr'], event.dungeon_name)
        else:
            return autoevent['searchstr'].lower() in event.clean_dungeon_name.lower() \
                   or autoevent['searchstr'].lower() in event.dungeon_name.lower()

    @commands.group(aliases=['aep'])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def autoeventping(self, ctx):
        """Auto Event Pings"""

    @autoeventping.command(name="add", ignore_extra=False)
    async def aep_add(self, ctx, key, server: Server = None, searchstr=None,
                      role: Optional[discord.Role] = None,
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

        default = {
            'role': None,
            'channel': (channel or ctx.channel).id,
            'server': server or 'NA',
            'searchstr': searchstr and rmdiacritics(searchstr),
            'regex': False,
            'enabled': bool(role or channel),
            'offset': 0,
        }

        if role is not None:
            default['role'] = role.id

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
        role = (ctx.guild.get_role(pingroles[key]['role']).mention
                if ctx.guild.get_role(pingroles[key]['role']) is not None
                else "No Role")
        channel = (ctx.bot.get_channel(pingroles[key]['channel']).mention
                   if ctx.bot.get_channel(pingroles[key]['channel']) is not None
                   else "No Channel")
        pr = (f"Key: `{key}`\n"
              f"\tStatus: {YES_EMOJI + ' enabled' if pingroles[key]['enabled'] else NO_EMOJI + ' disabled'}\n"
              f"\tSearch string: `{pingroles[key]['searchstr']}` {'(regex search)' * pingroles[key]['regex']}\n"
              f"\tServer: {pingroles[key]['server']}\n"
              f"\tRed: {role} (In {channel})\n"
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

    async def aepset(self, ctx, key: str, k: str, v: Any):
        async with self.config.guild(ctx.guild).pingroles() as pingroles:
            if key not in pingroles:
                await ctx.send("That key does not exist.")
                return
            pingroles[key][k] = v
        await ctx.tick()

    async def aepget(self, ctx, key: str):
        pingroles = await self.config.guild(ctx.guild).pingroles()
        if key not in pingroles:
            raise ClientInlineTextException(f"Key `{key}` does not exist.  Available keys are:"
                                            f" {', '.join(map(inline, pingroles))}")
        return pingroles[key]

    @aep_set.command(name="channel")
    async def aep_s_channel(self, ctx, key, channel: discord.TextChannel):
        """Sets channel to ping"""
        await self.aepset(ctx, key, 'channel', channel.id)

    @aep_set.command(name="roles")
    async def aep_s_roles(self, ctx, key, role: discord.Role):
        """Sets roles to ping"""
        await self.aepset(ctx, key, 'role', role.id)

    @aep_set.command(name="server")
    async def aep_s_server(self, ctx, key, server: Server):
        """Sets which server to listen to events in"""
        server = server.value
        await self.aepset(ctx, key, 'server', server)

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

    @aep_set.command(name="enabled", aliases=['enable'])
    async def aep_s_enabled(self, ctx, key, enabled: bool = True):
        """Sets whether or not ping is enabled"""
        await self.aepset(ctx, key, 'enabled', enabled)

    @aep_set.command(name="disabled", aliases=['disable'])
    async def aep_s_disabled(self, ctx, key, disabled: bool = True):
        """Sets whether or not ping is disabled"""
        await self.aepset(ctx, key, 'enabled', not disabled)

    @aep_set.command(name="offset")
    async def aep_s_offset(self, ctx, key, offset: int):
        """Sets how many minutes before event should ping happen"""
        if offset < 0:
            await ctx.send("Offset cannot be negative.")
            return
        await self.aepset(ctx, key, 'offset', offset)

    @autoeventping.command(name="channelmessage")
    async def aep_channelmessage(self, ctx, channel: Optional[discord.TextChannel], enable: bool):
        """Whether to show daily AEP summaries"""
        await self.config.channel(channel or ctx.channel).do_aep_post.set(enable)
        await ctx.tick()

    @commands.group(aliases=['aed'])
    async def autoeventdm(self, ctx):
        """Auto Event DMs"""

    @autoeventdm.command(name="add")
    async def aed_add(self, ctx, server: Server, searchstr, time_offset: int = 0):
        """Add a new autoeventdm"""
        server = server.value

        if time_offset and not user_is_donor(ctx):
            await ctx.send("You must be a donor to set a time offset!")
            return
        if time_offset < 0:
            await ctx.send("Offset cannot be negative")
            return

        default = {
            'key': time.time(),
            'server': server,
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
                    await send_cancellation_message(ctx, f"That string did not match any existing patterns."
                                                         f" Printing all of your Auto Event DMs (you can also"
                                                         f" see this with `{ctx.prefix}autoeventdm list`):")
                    await self.aed_list(ctx)
                    return None
        return user_index - 1
