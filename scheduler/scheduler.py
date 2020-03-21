from __future__ import annotations

"""
To anyone that comes to this later to improve it, the number one improvement
which can be made is to stop storing just a unix timestamp.
Store a naive time tuple(limited granularity to seconds) with timezone code instead.
The scheduling logic itself is solid, even if not the easiest to reason about.
The patching of discord.TextChannel and fake discord.Message objects is *messy* but works.
  - Sinbad


Oh god, this is a mess of dependancies mashed together into one precarious piece of code.
Honestly, I have no idea what half of it does, and I don't wanna spend the time to figure
it out.  Just pray it doesn't break I guess?  Good luck to anyone who wants to maintain this.
I honestly recommend that you just make a new one and delete this unholy thousand line piece
of code.
  - Droon
"""

import asyncio
import contextlib
import functools
import logging
import argparse
import dataclasses
import attr
import re
import pytz
from dateutil import parser
from dateutil.tz import gettz
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, NamedTuple, cast, Union

import discord
from redbot.core import commands, checks
from redbot.core.config import Config
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import humanize_timedelta

from redbot.core.commands import Context, BadArgument

class NonNumeric(NamedTuple):
    parsed: str

    @classmethod
    async def convert(cls, context: Context, argument: str):
        if argument.isdigit():
            raise BadArgument("Event names must contain at least 1 non-numeric value")
        return cls(argument)


@dataclasses.dataclass()
class Schedule:
    start: datetime
    command: str
    recur: Optional[timedelta] = None
    quiet: bool = False

    def to_tuple(self) -> Tuple[str, datetime, Optional[timedelta]]:
        return self.command, self.start, self.recur

    @classmethod
    async def convert(cls, ctx: Context, argument: str):

        start: datetime
        command: Optional[str] = None
        recur: Optional[timedelta] = None

        # Blame iOS smart punctuation,
        # and end users who use it for this (minor) perf loss
        argument = argument.replace("—", "--")

        command, *arguments = argument.split(" -- ")
        if arguments:
            argument = " -- ".join(arguments)
        else:
            command = None

        parser = NoExitParser(description="Scheduler event parsing", add_help=False)
        parser.add_argument(
            "-q", "--quiet", action="store_true", dest="quiet", default=False
        )
        parser.add_argument("--every", nargs="*", dest="every", default=[])
        if not command:
            parser.add_argument("command", nargs="*")
        at_or_in = parser.add_mutually_exclusive_group()
        at_or_in.add_argument("--start-at", nargs="*", dest="at", default=[])
        at_or_in.add_argument("--start-in", nargs="*", dest="in", default=[])

        try:
            vals = vars(parser.parse_args(argument.split(" ")))
        except Exception as exc:
            raise BadArgument() from exc

        if not (vals["at"] or vals["in"]):
            raise BadArgument("You must provide one of `--start-in` or `--start-at`")

        if not command and not vals["command"]:
            raise BadArgument("You have to provide a command to run")

        command = command or " ".join(vals["command"])

        for delta in ("in", "every"):
            if vals[delta]:
                parsed = parse_timedelta(" ".join(vals[delta]))
                if not parsed:
                    raise BadArgument("I couldn't understand that time interval")

                if delta == "in":
                    start = datetime.now(timezone.utc) + parsed
                else:
                    recur = parsed
                    if recur.total_seconds() < 60:
                        raise BadArgument(
                            "You can't schedule something to happen that frequently, "
                            "I'll get ratelimited."
                        )

        if vals["at"]:
            try:
                start = parse_time(" ".join(vals["at"]))
            except Exception:
                raise BadArgument("I couldn't understand that starting time.") from None

        return cls(command=command, start=start, recur=recur, quiet=vals["quiet"])

def can_run_command(command_name: str):
    async def predicate(ctx):

        command = ctx.bot.get_command(command_name)
        if not command:
            return False

        try:
            can_run = await command.can_run(
                ctx, check_all_parents=True, change_permission_state=False
            )
        except commands.CommandError:
            can_run = False

        return can_run

    return commands.check(predicate)

@attr.s(auto_attribs=True, slots=True)
class Task:
    nicename: str
    uid: str
    author: discord.Member
    content: str
    channel: discord.TextChannel
    initial: datetime
    recur: Optional[timedelta] = None

    def __attrs_post_init__(self):
        if self.initial.tzinfo is None:
            self.initial = self.initial.replace(tzinfo=timezone.utc)

    def __hash__(self):
        return hash(self.uid)

    async def get_message(self, bot):

        pfx = (await bot.get_prefix(self.channel))[0]
        content = f"{pfx}{self.content}"
        return SchedulerMessage(
            content=content, author=self.author, channel=self.channel
        )

    def to_config(self):

        return {
            self.uid: {
                "nicename": self.nicename,
                "author": self.author.id,
                "content": self.content,
                "channel": self.channel.id,
                "initial": self.initial.timestamp(),
                "recur": self.recur.total_seconds() if self.recur else None,
            }
        }

    @classmethod
    def bulk_from_config(cls, bot: discord.Client, **entries):

        for uid, data in entries.items():
            cid = data.pop("channel", 0)
            aid = data.pop("author", 0)
            initial_ts = data.pop("initial", 0)
            initial = datetime.fromtimestamp(initial_ts, tz=timezone.utc)
            recur_raw = data.pop("recur", None)
            recur = timedelta(seconds=recur_raw) if recur_raw else None

            channel = cast(Optional[discord.TextChannel], bot.get_channel(cid))
            if not channel:
                continue

            author = channel.guild.get_member(aid)
            if not author:
                continue

            with contextlib.suppress(AttributeError, ValueError):
                yield cls(
                    initial=initial,
                    recur=recur,
                    channel=channel,
                    author=author,
                    uid=uid,
                    **data,
                )

    @property
    def next_call_delay(self) -> float:

        now = datetime.now(timezone.utc)

        if self.recur and now >= self.initial:
            raw_interval = self.recur.total_seconds()
            return raw_interval - ((now - self.initial).total_seconds() % raw_interval)

        return (self.initial - now).total_seconds()

    def to_embed(self, index: int, page_count: int, color: discord.Color):

        now = datetime.now(timezone.utc)
        next_run_at = now + timedelta(seconds=self.next_call_delay)
        embed = discord.Embed(color=color, timestamp=next_run_at)
        embed.title = f"Now viewing {index} of {page_count} selected tasks"
        embed.add_field(name="Command", value=f"[p]{self.content}")
        embed.add_field(name="Channel", value=self.channel.mention)
        embed.add_field(name="Creator", value=self.author.mention)
        embed.add_field(name="Task ID", value=self.uid)

        try:
            fmt_date = self.initial.strftime("%A %B %-d, %Y at %-I%p %Z")
        except ValueError:  # Windows
            # This looks less natural, but I'm not doing this piecemeal to emulate.
            fmt_date = self.initial.strftime("%A %B %d, %Y at %I%p %Z")

        if self.recur:
            try:
                fmt_date = self.initial.strftime("%A %B %-d, %Y at %-I%p %Z")
            except ValueError:  # Windows
                # This looks less natural, but I'm not doing this piecemeal to emulate.
                fmt_date = self.initial.strftime("%A %B %d, %Y at %I%p %Z")

            if self.initial > now:
                description = (
                    f"{self.nicename} starts running on {fmt_date}."
                    f"\nIt repeats every {humanize_timedelta(timedelta=self.recur)}"
                )
            else:
                description = (
                    f"{self.nicename} started running on {fmt_date}."
                    f"\nIt repeats every {humanize_timedelta(timedelta=self.recur)}"
                )
            footer = "Next runtime:"
        else:
            try:
                fmt_date = next_run_at.strftime("%A %B %-d, %Y at %-I%p %Z")
            except ValueError:  # Windows
                # This looks less natural, but I'm not doing this piecemeal to emulate.
                fmt_date = next_run_at.strftime("%A %B %d, %Y at %I%p %Z")
            description = f"{self.nicename} will run at {fmt_date}."
            footer = "Runtime:"

        embed.set_footer(text=footer)
        embed.description = description
        return embed

    def update_objects(self, bot):
        """ Updates objects or throws an AttributeError """
        guild_id = self.author.guild.id
        author_id = self.author.id
        channel_id = self.channel.id

        guild = bot.get_guild(guild_id)
        self.author = guild.get_member(author_id)
        self.channel = guild.get_channel(channel_id)
        if not hasattr(self.channel, "id"):
            raise AttributeError()
        # Yes, this is slower than an inline `self.channel.id`
        # It's also not slow anywhere important, and I prefer the clear intent

class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()


class TempMute(NamedTuple):
    reason: Optional[str]
    start: datetime

    @classmethod
    async def convert(cls, ctx: Context, argument: str):

        start: datetime
        reason: str

        # Blame iOS smart punctuation,
        # and end users who use it for this (minor) perf loss
        argument = argument.replace("—", "--")

        parser = NoExitParser(description="Scheduler event parsing", add_help=False)
        parser.add_argument("reason", nargs="*")
        at_or_in = parser.add_mutually_exclusive_group()
        at_or_in.add_argument("--until", nargs="*", dest="until", default=[])
        at_or_in.add_argument("--for", nargs="*", dest="for", default=[])

        try:
            vals = vars(parser.parse_args(argument.split()))
        except Exception as exc:
            raise BadArgument() from exc

        if not (vals["until"] or vals["for"]):
            raise BadArgument("You must provide one of `--until` or `--for`")

        reason = " ".join(vals["reason"])

        if vals["for"]:
            parsed = parse_timedelta(" ".join(vals["for"]))
            if not parsed:
                raise BadArgument("I couldn't understand that time interval")
            start = datetime.now(timezone.utc) + parsed

        if vals["until"]:
            try:
                start = parse_time(" ".join(vals["at"]))
            except Exception:
                raise BadArgument("I couldn't understand that unmute time.") from None

        return cls(reason, start)


TIME_RE_STRING = r"\s?".join(
    [
        r"((?P<weeks>\d+?)\s?(weeks?|w))?",
        r"((?P<days>\d+?)\s?(days?|d))?",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))?",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m(?!o)))?",  # prevent matching "months"
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))?",
    ]
)

TIME_RE = re.compile(TIME_RE_STRING, re.I)


def gen_tzinfos():
    for zone in pytz.common_timezones:
        try:
            tzdate = pytz.timezone(zone).localize(datetime.utcnow(), is_dst=None)
        except pytz.NonExistentTimeError:
            pass
        else:
            tzinfo = gettz(zone)

            if tzinfo:
                yield tzdate.tzname(), tzinfo


def parse_time(datetimestring: str):
    ret = parser.parse(datetimestring, tzinfos=dict(gen_tzinfos()))
    ret = ret.astimezone(pytz.utc)
    return ret


def parse_timedelta(argument: str) -> Optional[timedelta]:
    matches = TIME_RE.match(argument)
    if matches:
        params = {k: int(v) for k, v in matches.groupdict().items() if v}
        if params:
            return timedelta(**params)
    return None

EVERYONE_REGEX = re.compile(r"@here|@everyone")


async def dummy_awaitable(*args, **kwargs):
    return


def neuter_coroutines(klass):
    # I might forget to modify this with discord.py updates, so lets automate it.

    for attr in dir(klass):
        _ = getattr(klass, attr, None)
        if asyncio.iscoroutinefunction(_):

            def dummy(self):
                return dummy_awaitable

            prop = property(fget=dummy)
            setattr(klass, attr, prop)
    return klass

# This entire below block is such an awful hack. Don't look at it too closely.


@neuter_coroutines
class SchedulerMessage(discord.Message):
    """
    Subclassed discord message with neutered coroutines.
    Extremely butchered class for a specific use case.
    Be careful when using this in other use cases.
    """

    def __init__(
        self, *, content: str, author: discord.Member, channel: discord.TextChannel
    ) -> None:
        # auto current time
        self.id = discord.utils.time_snowflake(datetime.utcnow())
        # important properties for even being processed
        self.author = author
        self.channel = channel
        self.content = content
        self.guild = channel.guild  # type: ignore
        # this attribute being in almost everything (and needing to be) is a pain
        self._state = self.guild._state  # type: ignore
        # sane values below, fresh messages which are commands should exhibit these.
        self.call = None
        self.type = discord.MessageType.default
        self.tts = False
        self.pinned = False
        # suport for attachments somehow later maybe?
        self.attachments: List[discord.Attachment] = []
        # mentions
        self.mention_everyone = self.channel.permissions_for(
            self.author
        ).mention_everyone and bool(EVERYONE_REGEX.match(self.content))
        # pylint: disable=E1133
        # pylint improperly detects the inherited properties here as not being iterable
        # This should be fixed with typehint support added to upstream lib later
        self.mentions: List[Union[discord.User, discord.Member]] = list(
            filter(None, [self.guild.get_member(idx) for idx in self.raw_mentions])
        )
        self.channel_mentions: List[discord.TextChannel] = list(
            filter(
                None,
                [
                    self.guild.get_channel(idx)  # type: ignore
                    for idx in self.raw_channel_mentions
                ],
            )
        )
        self.role_mentions: List[discord.Role] = list(
            filter(None, [self.guild.get_role(idx) for idx in self.raw_role_mentions])
        )


class Scheduler(commands.Cog):
    """
    A somewhat sane scheduler cog.
    This cog is no longer supported.
    Details as to why are available at source.
    As of time of marked unsupported,
    the cog was functional and not expected to be fragile to changes.
    This cog has a known issue with timezone transtions that will not be fixed.
    """

    __author__ = "mikeshardmind(Sinbad), DiscordLiz"
    __version__ = "330.0.2"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot, *args, **kwargs):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_channel(tasks={})  # Serialized Tasks go in here.
        self.log = logging.getLogger("red.sinbadcogs.scheduler")
        self.bg_loop_task: Optional[asyncio.Task] = None
        self.scheduled: Dict[
            str, asyncio.Task
        ] = {}  # Might change this to a list later.
        self.tasks: List[Task] = []
        self._iter_lock = asyncio.Lock()

    def init(self):
        self.bg_loop_task = asyncio.create_task(self.bg_loop())

    def cog_unload(self):
        if self.bg_loop_task:
            self.bg_loop_task.cancel()
        for task in self.scheduled.values():
            task.cancel()

    async def _load_tasks(self):
        chan_dict = await self.config.all_channels()
        for channel_id, channel_data in chan_dict.items():
            channel = self.bot.get_channel(channel_id)
            if (
                not channel
                or not channel.permissions_for(channel.guild.me).read_messages
            ):
                continue
            tasks_dict = channel_data.get("tasks", {})
            for t in Task.bulk_from_config(bot=self.bot, **tasks_dict):
                self.tasks.append(t)

    async def _remove_tasks(self, *tasks: Task):
        async with self._iter_lock:
            for task in tasks:
                self.tasks.remove(task)
                await self.config.channel(task.channel).clear_raw("tasks", task.uid)

    async def bg_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)
        _guilds = [
            g for g in self.bot.guilds if g.large and not (g.chunked or g.unavailable)
        ]
        await self.bot.request_offline_members(*_guilds)

        async with self._iter_lock:
            await self._load_tasks()
        while True:
            sleep_for = await self.schedule_upcoming()
            await asyncio.sleep(sleep_for)

    async def delayed_wrap_and_invoke(self, task: Task, delay: float):
        await asyncio.sleep(delay)
        task.update_objects(self.bot)
        chan = task.channel
        if not chan.permissions_for(chan.guild.me).read_messages:
            return
        message = await task.get_message(self.bot)
        context = await self.bot.get_context(message)
        context.assume_yes = True
        await self.bot.invoke(context)
        for cog_name in ("CustomCommands", "Alias"):
            cog = self.bot.get_cog(cog_name)
            if cog:
                await cog.on_message(message)
        # TODO: allow registering additional cogs to process on_message for.

    async def schedule_upcoming(self) -> int:
        """
        Schedules some upcoming things as tasks.
        """

        # TODO: improve handlng of next time return

        async with self._iter_lock:
            to_pop = []
            for k, v in self.scheduled.items():
                if v.done():
                    to_pop.append(k)
                    try:
                        v.result()
                    except Exception:
                        self.log.exception("Dead task ", exc_info=True)

            for k in to_pop:
                self.scheduled.pop(k, None)

        to_remove: list = []

        for task in self.tasks:
            delay = task.next_call_delay
            if delay < 30 and task.uid not in self.scheduled:
                self.scheduled[task.uid] = asyncio.create_task(
                    self.delayed_wrap_and_invoke(task, delay)
                )
                if not task.recur:
                    to_remove.append(task)

        await self._remove_tasks(*to_remove)

        return 15

    async def fetch_task_by_attrs_exact(self, **kwargs) -> List[Task]:
        def pred(item):
            try:
                return kwargs and all(getattr(item, k) == v for k, v in kwargs.items())
            except AttributeError:
                return False

        async with self._iter_lock:
            return [t for t in self.tasks if pred(t)]

    async def fetch_task_by_attrs_lax(
        self, lax: Optional[dict] = None, strict: Optional[dict] = None
    ) -> List[Task]:
        def pred(item):
            try:
                if strict and not all(getattr(item, k) == v for k, v in strict.items()):
                    return False
            except AttributeError:
                return False
            if lax:
                return any(getattr(item, k, None) == v for k, v in lax.items())
            return True

        async with self._iter_lock:
            return [t for t in self.tasks if pred(t)]

    async def fetch_tasks_by_guild(self, guild: discord.Guild) -> List[Task]:

        async with self._iter_lock:
            return [t for t in self.tasks if t.channel in guild.text_channels]

    # Commands go here

    @checks.mod_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.command(usage="<eventname> <command> <args>")
    async def schedule(
        self, ctx: commands.GuildContext, event_name: NonNumeric, *, schedule: Schedule
    ):
        """
        Schedule something
        Usage:
            [p]schedule eventname command args
        args:
            you must provide one of:
                --start-in interval
                --start-at time
            you may also provide:
                --every interval
            for recurring tasks
        intervals look like:
            5 minutes
            1 minute 30 seconds
            1 hour
            2 days
            30 days
            (etc)
        times look like:
            February 14 at 6pm EDT
        times default to UTC if no timezone provided.
        Example use:
            [p]schedule autosync bansync True --start-at 12AM --every 1 day
        Example use with other parsed commands:
        [p]schedule autosyndicate syndicatebans --sources 133049272517001216 --auto-destinations -- --start-at 12AM --every 1 hour
        This can also execute aliases.
        """

        command, start, recur = schedule.to_tuple()

        t = Task(
            uid=str(ctx.message.id),
            nicename=event_name.parsed,
            author=ctx.author,
            content=command,
            channel=ctx.channel,
            initial=start,
            recur=recur,
        )

        quiet: bool = schedule.quiet or ctx.assume_yes

        if await self.fetch_task_by_attrs_exact(
            author=ctx.author, channel=ctx.channel, nicename=event_name.parsed
        ):
            if not quiet:
                return await ctx.send("You already have an event by that name here.")

        async with self._iter_lock:
            async with self.config.channel(ctx.channel).tasks(
                acquire_lock=False
            ) as tsks:
                tsks.update(t.to_config())
            self.tasks.append(t)

        if quiet:
            return

        ret = (
            f"Task Scheduled. You can cancel this task with "
            f"`{ctx.clean_prefix}unschedule {ctx.message.id}` "
            f"or with `{ctx.clean_prefix}unschedule {event_name.parsed}`"
        )

        if recur and t.next_call_delay < 60:
            ret += (
                "\nWith the intial start being set so soon, "
                "you might have missed an initial use being scheduled by the loop. "
                "you may find the very first expected run of this was missed or otherwise seems late. "
                "Future runs will be on time."  # fractions of a second in terms of accuracy.
            )

        await ctx.send(ret)

    @commands.guild_only()
    @commands.command()
    async def unschedule(self, ctx: commands.GuildContext, info: str):
        """
        unschedule something.
        """

        quiet: bool = ctx.assume_yes

        tasks = await self.fetch_task_by_attrs_lax(
            lax={"uid": info, "nicename": info},
            strict={"author": ctx.author, "channel": ctx.channel},
        )

        if not tasks and not quiet:
            await ctx.send(
                f"Hmm, I couldn't find that task. (try `{ctx.clean_prefix}showscheduled`)"
            )

        elif len(tasks) > 1:
            self.log.warning(
                f"Mutiple tasks where should be unique. Task data: {tasks}"
            )
            if not quiet:
                await ctx.send(
                    "There seems to have been breakage here. "
                    "Cleaning up and logging incident."
                )
            return

        else:
            await self._remove_tasks(*tasks)
            if not quiet:
                await ctx.tick()

    @checks.bot_has_permissions(add_reactions=True, embed_links=True)
    @commands.guild_only()
    @commands.command()
    async def showscheduled(
        self, ctx: commands.GuildContext, all_channels: bool = False
    ):
        """ shows your scheduled tasks in this, or all channels """

        if all_channels:
            tasks = await self.fetch_tasks_by_guild(ctx.guild)
            tasks = [t for t in tasks if t.author == ctx.author]
        else:
            tasks = await self.fetch_task_by_attrs_exact(
                author=ctx.author, channel=ctx.channel
            )

        if not tasks:
            return await ctx.send("No scheduled tasks")

        await self.task_menu(ctx, tasks)

    async def task_menu(
        self,
        ctx: commands.GuildContext,
        tasks: List[Task],
        message: Optional[discord.Message] = None,
    ):

        color = await ctx.embed_color()

        async def task_killer(
            cog: "Scheduler",
            page_mapping: dict,
            ctx: commands.GuildContext,
            pages: list,
            controls: dict,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            to_cancel = page_mapping.pop(page)
            await cog._remove_tasks(to_cancel)
            if page_mapping:
                tasks = list(page_mapping.values())
                if ctx.channel.permissions_for(ctx.me).manage_messages:
                    with contextlib.suppress(discord.HTTPException):
                        await message.remove_reaction("\N{NO ENTRY SIGN}", ctx.author)
                await cog.task_menu(ctx, tasks, message)
            else:
                with contextlib.suppress(discord.NotFound):
                    await message.delete()

        count = len(tasks)
        embeds = [
            t.to_embed(index=i, page_count=count, color=color)
            for i, t in enumerate(tasks, 1)
        ]

        controls = DEFAULT_CONTROLS.copy()
        page_mapping = {i: t for i, t in enumerate(tasks)}
        actual_task_killer = functools.partial(task_killer, self, page_mapping)
        controls.update({"\N{NO ENTRY SIGN}": actual_task_killer})
        await menu(ctx, embeds, controls, message=message)

    @commands.check(lambda ctx: ctx.message.__class__.__name__ == "SchedulerMessage")
    @commands.group(hidden=True, name="schedhelpers")
    async def helpers(self, ctx: commands.GuildContext):
        """ helper commands for scheduler use """
        pass

    @helpers.command(name="say")
    async def say(self, ctx: commands.GuildContext, *, content: str):
        await ctx.send(content)

    @helpers.command(name="selfwhisper")
    async def swhisp(self, ctx: commands.GuildContext, *, content: str):
        with contextlib.suppress(discord.HTTPException):
            await ctx.author.send(content)

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group()
    async def scheduleradmin(self, ctx: commands.GuildContext):
        """ Administrative commands for scheduler """
        pass

    @checks.bot_has_permissions(add_reactions=True, embed_links=True)
    @scheduleradmin.command()
    async def viewall(self, ctx: commands.GuildContext):
        """ view all scheduled events in a guild """

        tasks = await self.fetch_tasks_by_guild(ctx.guild)

        if not tasks:
            return await ctx.send("No scheduled tasks")

        await self.task_menu(ctx, tasks)

    @scheduleradmin.command()
    async def kill(self, ctx: commands.GuildContext, *, task_id: str):
        """ kill another user's task (id only) """

        tasks = await self.fetch_task_by_attrs_exact(uid=task_id)

        if not tasks:
            await ctx.send(
                f"Hmm, I couldn't find that task. (try `{ctx.clean_prefix}showscheduled`)"
            )

        elif len(tasks) > 1:
            self.log.warning(
                f"Mutiple tasks where should be unique. Task data: {tasks}"
            )
            return await ctx.send(
                "There seems to have been breakage here. Cleaning up and logging incident."
            )

        else:
            await self._remove_tasks(*tasks)
            await ctx.tick()

    @scheduleradmin.command()
    async def killchannel(self, ctx, channel: discord.TextChannel):
        """ kill all in a channel """

        tasks = await self.fetch_task_by_attrs_exact(channel=channel)

        if not tasks:
            return await ctx.send("No scheduled tasks in that channel.")

        await self._remove_tasks(*tasks)
        await ctx.tick()

    @commands.guild_only()
    @commands.group()
    async def tempmute(self, ctx):
        """
        binding for mute + scheduled unmute
        This exists only until it is added to core red
        relies on core commands for mute/unmute
        This *may* show up in help for people who cannot use it.
        This does not support voice mutes, sorry.
        """
        pass

    @can_run_command("mute channel")
    @tempmute.command(usage="<user> [reason] [args]")
    async def channel(self, ctx, user: discord.Member, *, mute: TempMute):
        """
        binding for mute + scheduled unmute
        This exists only until it is added to core red
        args can be
            --until time
        or
            --for interval
        intervals look like:
            5 minutes
            1 minute 30 seconds
            1 hour
            2 days
            30 days
            (etc)
        times look like:
            February 14 at 6pm EDT
        times default to UTC if no timezone provided.
        """

        reason, unmute_time = mute

        now = datetime.now(timezone.utc)

        mute_task = Task(
            uid=f"mute-{ctx.message.id}",
            nicename=f"mute-{ctx.message.id}",
            author=ctx.author,
            content=f"mute channel {user.id} {reason}",
            channel=ctx.channel,
            initial=now,
            recur=None,
        )

        unmute_task = Task(
            uid=f"unmute-{ctx.message.id}",
            nicename=f"unmute-{ctx.message.id}",
            author=ctx.author,
            content=f"unmute channel {user.id} Scheduler: Scheduled Unmute",
            channel=ctx.channel,
            initial=unmute_time,
            recur=None,
        )

        async with self._iter_lock:
            self.scheduled[mute_task.uid] = asyncio.create_task(
                self.delayed_wrap_and_invoke(mute_task, 0)
            )

            async with self.config.channel(ctx.channel).tasks(
                acquire_lock=False
            ) as tsks:
                tsks.update(unmute_task.to_config())
            self.tasks.append(unmute_task)

    @can_run_command("mute server")
    @tempmute.command(usage="<user> [reason] [args]", aliases=["guild"])
    async def server(self, ctx, user: discord.Member, *, mute: TempMute):
        """
        binding for mute + scheduled unmute
        This exists only until it is added to core red
        args can be
            --until time
        or
            --for interval
        intervals look like:
            5 minutes
            1 minute 30 seconds
            1 hour
            2 days
            30 days
            (etc)
        times look like:
            February 14 at 6pm EDT
        times default to UTC if no timezone provided.
        """

        reason, unmute_time = mute

        now = datetime.now(timezone.utc)

        mute_task = Task(
            uid=f"mute-{ctx.message.id}",
            nicename=f"mute-{ctx.message.id}",
            author=ctx.author,
            content=f"mute server {user.id} {reason}",
            channel=ctx.channel,
            initial=now,
            recur=None,
        )

        unmute_task = Task(
            uid=f"unmute-{ctx.message.id}",
            nicename=f"unmute-{ctx.message.id}",
            author=ctx.author,
            content=f"unmute server {user.id} Scheduler: Scheduled Unmute",
            channel=ctx.channel,
            initial=unmute_time,
            recur=None,
        )

        async with self._iter_lock:
            self.scheduled[mute_task.uid] = asyncio.create_task(
                self.delayed_wrap_and_invoke(mute_task, 0)
            )

            async with self.config.channel(ctx.channel).tasks(
                acquire_lock=False
            ) as tsks:
                tsks.update(unmute_task.to_config())
            self.tasks.append(unmute_task)
