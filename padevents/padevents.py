import asyncio
import datetime
import logging
import time
from collections import defaultdict
from contextlib import suppress
from datetime import timedelta
from io import BytesIO
from typing import Any, NoReturn, Optional

import discord
import prettytable
import pytz
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box, pagify
from tsutils.enums import Server, StarterGroup
from tsutils.formatting import normalize_server_name
from tsutils.helper_classes import DummyObject
from tsutils.helper_functions import conditional_iterator, repeating_timer

from padevents.autoevent_mixin import AutoEvent
from padevents.events import Event, EventList, SERVER_TIMEZONES
from padevents.enums import DungeonType, EventLength

logger = logging.getLogger('red.padbot-cogs.padevents')

SUPPORTED_SERVERS = ["JP", "NA", "KR"]
GROUPS = ['red', 'blue', 'green']


class PadEvents(commands.Cog, AutoEvent):
    """Pad Event Tracker"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=940373775)
        self.config.register_global(sent={}, last_daychange=None)
        self.config.register_guild(pingroles={})
        self.config.register_channel(guerrilla_servers=[], daily_servers=[])
        self.config.register_user(dmevents=[])

        # Load event data
        self.events = list()
        self.started_events = set()

        self.fake_uid = -time.time()

        self._event_loop = bot.loop.create_task(self.reload_padevents())
        self._refresh_loop = bot.loop.create_task(self.do_loop())
        self._daily_event_loop = bot.loop.create_task(self.show_daily_info())

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
        self._daily_event_loop.cancel()

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

    async def show_daily_info(self) -> NoReturn:
        async def is_day_change():
            curserver = self.get_most_recent_day_change()
            oldserver = self.config.last_daychange
            if curserver != await oldserver():
                await oldserver.set(curserver)
                return curserver

        await self.bot.wait_until_ready()
        with suppress(asyncio.CancelledError):
            async for server in conditional_iterator(is_day_change, poll_interval=10):
                try:
                    await self.do_daily_post(server)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Error in loop:")

    async def refresh_data(self):
        dbcog: Any = self.bot.get_cog('DBCog')
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

    async def do_eventloop(self):
        events = filter(lambda e: e.is_started() and e.key not in self.started_events, self.events)
        daily_refresh_servers = set()
        for event in events:
            self.started_events.add(event.key)
            if event.event_length != EventLength.limited:
                continue
            for cid, data in (await self.config.all_channels()).items():
                if (channel := self.bot.get_channel(cid)) is None \
                        or event.server not in data['guerrilla_servers']:
                    continue
                role_name = f'{event.server}_group_{event.group_long_name()}'
                role = channel.guild.get_role(role_name)
                if role and role.mentionable:
                    message = f"{role.mention} {event.name_and_modifier} is starting"
                else:
                    message = box(f"Server {event.server}, group {event.group_long_name()}:"
                                  f" {event.name_and_modifier}")
                with suppress(discord.Forbidden):
                    await channel.send(message, allowed_mentions=discord.AllowedMentions(roles=True))

    async def do_daily_post(self, server):
        msg = self.make_active_text(server)
        for cid, data in (await self.config.all_channels()).items():
            if (channel := self.bot.get_channel(cid)) is None \
                    or server not in data['daily_servers']:
                continue
            for page in pagify(msg, delims=['\n\n']):
                with suppress(discord.Forbidden):
                    await channel.send(box(page))

    @commands.group(aliases=['pde'])
    @checks.mod_or_permissions(manage_guild=True)
    async def padevents(self, ctx):
        """PAD event tracking"""

    @padevents.command()
    @checks.is_owner()
    async def testevent(self, ctx, server: Server, seconds: int = 0):
        server = server.value

        dbcog: Any = self.bot.get_cog('DBCog')
        await dbcog.wait_until_ready()
        # TODO: Don't use this awful importing hack
        dg_module = __import__('.'.join(dbcog.__module__.split('.')[:-1]) + ".models.scheduled_event_model")
        timestamp = int((datetime.datetime.now(pytz.utc) + timedelta(seconds=seconds)).timestamp())
        self.fake_uid -= 1

        te = dg_module.models.scheduled_event_model.ScheduledEventModel(
            event_id=self.fake_uid,
            server_id=SUPPORTED_SERVERS.index(server),
            event_type_id=-1,
            start_timestamp=timestamp,
            end_timestamp=timestamp + 60,
            group_name='red',
            dungeon_model=DummyObject(
                name_en='fake_dungeon_name',
                clean_name_en='fake_dungeon_name',
                dungeon_type=DungeonType.ThreePlayer,
                dungeon_id=1,
            )
        )
        self.events.append(Event(te))
        await ctx.tick()

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addchannel(self, ctx, channel: Optional[discord.TextChannel], server: Server):
        server = server.value

        async with self.config.channel(channel or ctx.channel).guerrilla_servers() as guerillas:
            if server in guerillas:
                return await ctx.send("Channel already active.")
            guerillas.append(server)
        await ctx.send("Channel now active.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmchannel(self, ctx, channel: Optional[discord.TextChannel], server: Server):
        server = server.value

        async with self.config.channel(channel or ctx.channel).guerrilla_servers() as guerillas:
            if server not in guerillas:
                return await ctx.send("Channel already inactive.")
            guerillas.remove(server)
        await ctx.send("Channel now inactive.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addchanneldaily(self, ctx, channel: Optional[discord.TextChannel], server: Server):
        server = server.value

        async with self.config.channel(channel or ctx.channel).daily_servers() as dailies:
            if server in dailies:
                return await ctx.send("Channel already active.")
            dailies.append(server)
        await ctx.send("Channel now active.")

    @padevents.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmchanneldaily(self, ctx, channel: Optional[discord.TextChannel], server: Server):
        server = server.value

        async with self.config.channel(channel or ctx.channel).daily_servers() as dailies:
            if server not in dailies:
                return await ctx.send("Channel already inactive.")
            dailies.remove(server)
        await ctx.send("Channel now inactive.")

    @padevents.command()
    @checks.mod_or_permissions(manage_guild=True)
    async def active(self, ctx, server: Server):
        server = server.value

        msg = self.make_active_text(server)
        for page in pagify(msg, delims=['\n\n']):
            await ctx.send(box(page))

    def make_active_text(self, server):
        server = normalize_server_name(server)

        server_events = EventList(self.events).with_server(server)
        active_events = server_events.active_only()
        events_today = server_events.today_only(server)

        active_special = active_events.in_dungeon_type([DungeonType.Special])

        msg = server + " Events - " + datetime.datetime.now(SERVER_TIMEZONES[server]).strftime('%A, %B %e')

        ongoing_events = active_events.in_length([EventLength.weekly, EventLength.special])
        if ongoing_events:
            msg += "\n\n" + self.make_active_output('Ongoing Events', ongoing_events)

        active_dailies_events = active_events.with_length(EventLength.daily)
        if active_dailies_events:
            msg += "\n\n" + self.make_daily_output('Daily Dungeons', active_dailies_events)

        limited_events = events_today.with_length(EventLength.limited)
        if limited_events:
            msg += "\n\n" + self.make_full_guerrilla_output('Limited Events', limited_events)

        return msg

    def make_daily_output(self, table_name, event_list):
        tbl = prettytable.PrettyTable([table_name])
        tbl.hrules = prettytable.HEADER
        tbl.vrules = prettytable.NONE
        tbl.align[table_name] = "l"
        for e in event_list:
            tbl.add_row([e.name_and_modifier])
        return tbl.get_string()

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

    def make_full_guerrilla_output(self, table_name, event_list, starter_guerilla=True):
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

                if did_work and len(set(row)) == 2:  # One for Header and all three times are same
                    rows.append([row[0], row[1], '=', '='])
                elif did_work:
                    rows.append(row)
                else:
                    done = True

        col1 = "Limited"
        tbl = prettytable.PrettyTable([col1] + grps)
        tbl.align[col1] = "l"
        tbl.hrules = prettytable.HEADER
        tbl.vrules = prettytable.ALL

        for r in rows:
            tbl.add_row(r)

        header = "Times are PT below\n"
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
        events = events.in_dungeon_type([DungeonType.SoloSpecial, DungeonType.Special])
        events = events.is_grouped()

        active_events = events.active_only().items_by_open_time(reverse=True)
        pending_events = events.pending_only().items_by_open_time(reverse=True)

        if group is not None:
            active_events = [e for e in active_events if e.group == group.lower()]
            pending_events = [e for e in pending_events if e.group == group.lower()]

        group_to_active_event = {e.group: e for e in active_events}
        group_to_pending_event = {e.group: e for e in pending_events}

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

    def get_most_recent_day_change(self):
        now = datetime.datetime.utcnow().time()
        if now < datetime.time(8):
            return "JP"
        elif now < datetime.time(15):
            return "NA"
        elif now < datetime.time(16):
            return "KR"
        else:
            return "JP"


def make_channel_reg(channel_id, server):
    server = normalize_server_name(server)
    return {
        "channel_id": channel_id,
        "server": server
    }
