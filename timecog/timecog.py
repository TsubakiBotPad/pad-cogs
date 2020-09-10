import asyncio
import re
import time
import traceback
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta

import discord
import pytz
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import inline, pagify, box

import rpadutils

tz_lookup = dict([(pytz.timezone(x).localize(datetime.now()).tzname(), pytz.timezone(x))
                  for x in pytz.all_timezones])

time_at_regeces = [
    r'^\s*(?P<year>\d{4})[-/](?P<month>\d+)[-/](?P<day>\d+) (?P<hour>\d+):(?P<minute>\d\d) ?(?P<merid>pm|am)? ?(?P<input>.*)$',
    r'^\s*(?P<year>\d{4})[-/](?P<month>\d+)[-/](?P<day>\d+) ?(?P<input>.*)$',
    r'^\s*(?P<month>\d+)[-/](?P<day>\d+) ?(?P<input>.*)$',
    r'^\s*(?P<hour>\d+):(?P<minute>\d\d) ?(?P<merid>\d?pm|am)? ?(?P<input>.*)$',
    r'^\s*(?P<hour>\d+) ?(?P<merid>\d?pm|am) ?(?P<input>.*)$',
]

time_in_regeces = [
    r'^\s*((?:-?\d+ ?(?:m|h|d|w|y|s)\w* ?)+)\b (.+)$', # One tinstr
    r'^\s*((?:-?\d+ ?(?:m|h|d|w|y|s)\w* ?)+)\b\s*\|\s*((?:-?\d+ ?(?:m|h|d|w|y|s)\w* ?)+|now)\b (.*)$', #Unused
]

exact_tats = [
    r'^\s*(?P<year>\d{4})[-/](?P<month>\d+)[-/](?P<day>\d+) (?P<hour>\d+):(?P<minute>\d\d) ?(?P<merid>pm|am)?\s*$',
    r'^\s*(?P<year>\d{4})[-/](?P<month>\d+)[-/](?P<day>\d+)\s*$',
    r'^\s*(?P<month>\d+)[-/](?P<day>\d+)\s*$',
    r'^\s*(?P<hour>\d+):(?P<minute>\d\d) ?(?P<merid>\d?pm|am)?\s*$',
    r'^\s*(?P<hour>\d+) ?(?P<merid>\d?pm|am)\s*$',
]

exact_tins = [
    r'^\s*((?:-?\d+ ?(?:m|h|d|w|y|s)\w* ?)+)$', # One tinstr
]

DT_FORMAT = "%A, %b %-d, %Y at %-I:%M %p"
SHORT_DT_FORMAT = "%b %-d, %Y at %-I:%M %p"



class TimeCog(commands.Cog):
    """Utilities pertaining to time"""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = Config.get_conf(self, identifier=7173306)
        self.config.register_user(reminders=[], tz='')
        self.config.register_guild(schedules={})

        """
        CONFIG: Config
        |   USERS: Config
        |   |   reminders: list
        |   |   |   REMINDER: tuple
        |   |   |   |   TIME: int (timestamp)
        |   |   |   |   TEXT: str
        |   |   |   |   INTERVAL: Optional[int]
        |   |   tz: str (tzstr)
        |   CHANNELS: Config
        |   |   schedules: dict
        |   |   |   NAME: dict
        |   |   |   |   start: int (timestamp) (unused)
        |   |   |   |   time: int (timestamp)
        |   |   |   |   end: int (timestamp)
        |   |   |   |   interval: int (seconds)
        |   |   |   |   enabled: bool
        |   |   |   |   channels: list (cids)
        |   |   |   |   message: str
        """

        self.bot = bot

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        udata = await self.config.user_from_id(user_id).reminders()

        data = "You have {} reminder(s) set.\n".format(len(udata))

        if not udata:
            data = "No data is stored for user with ID {}.\n".format(user_id)

        return {"user_data.txt": BytesIO("data".encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data."""
        await self.config.user_from_id(user_id).clear()

    @commands.group(aliases=['remindmeat', 'remindmein'], invoke_without_command=True)
    async def remindme(self, ctx, *, time):
        """Reminds you to do something at a specified time

        [p]remindme 2020-04-13 06:12 Do something!
        [p]remindme 5 weeks Do something!
        [p]remindme 4:13 PM Do something!
        [p]remindme 2020-05-03 Do something!
        [p]remindme 04-13 Do something!
        """

        user_tz_str = await self.config.user(ctx.author).tz()
        user_timezone = tzstr_to_tz(user_tz_str or 'UTC')

        for ar in time_at_regeces:
            match = re.search(ar, time, re.IGNORECASE)
            if not match:
                continue
            match = match.groupdict()

            if not user_tz_str:
                await ctx.send(
                    "Please configure your personal timezone with `{0.clean_prefix}settimezone` first.".format(ctx))
                return

            now = datetime.now(tz=user_timezone)
            defaults = {
                'year': now.year,
                'month': now.month,
                'day': now.day,
                'hour': now.hour,
                'minute': now.minute,
                'merid': 'NONE'
            }
            defaults.update({k: v for k, v in match.items() if v})
            input = defaults.pop('input')
            for key in defaults:
                if key not in ['merid']:
                    defaults[key] = int(defaults[key])
            if defaults['merid'] == 'pm' and defaults['hour'] <= 12:
                defaults['hour'] += 12
            elif defaults['merid'] == 'NONE' and defaults['hour'] < now.hour:
                defaults['hour'] += 12
            if defaults['hour'] >= 24:
                defaults['day'] += int(defaults['hour'] // 24)
                defaults['hour'] = defaults['hour'] % 24
            del defaults['merid']
            try:
                rmtime = user_timezone.localize(datetime(**defaults))
            except ValueError as e:
                await ctx.send(inline(str(e).capitalize()))
                return
            if rmtime < now:
                rmtime += timedelta(days=1)
            rmtime = rmtime.astimezone(pytz.utc).replace(tzinfo=None)
            break
        else:
            ir = time_in_regeces[0]
            match = re.search(ir, time, re.IGNORECASE)
            if not match: # Only use the first one
                raise commands.UserFeedbackCheckFailure("Invalid time string: " + time)
            tinstrs, input = match.groups()
            rmtime = datetime.utcnow()
            try:
                rmtime += tin2tdelta(tinstrs)
            except OverflowError:
                raise commands.UserFeedbackCheckFailure(
                    inline("That's way too far in the future!  Please keep it in your lifespan!"))

        if rmtime < (datetime.utcnow() - timedelta(seconds=1)):
            raise commands.UserFeedbackCheckFailure(inline("You can't set a reminder in the past!  If only..."))

        async with self.config.user(ctx.author).reminders() as rms:
            rms.append((rmtime.timestamp(), input))

        response = "I will tell you " + format_rm_time(rmtime, input, user_timezone)
        if not user_tz_str:
            response += '. Configure your personal timezone with `{0.clean_prefix}settimezone` for accurate times.'.format(
                ctx)
        await ctx.send(response)

    @remindme.command(hidden=True)
    async def now(self, ctx, *, input):
        await ctx.author.send(input)

    @remindme.command()
    @checks.is_owner() #Command is unfinished
    async def every(self, ctx, *, text):
        await ctx.send("Test")
        match = re.search(time_in_regeces[1], text, re.IGNORECASE)
        if match:
            tinstrs, tinstart, input = match.groups()
        else:
            match = re.search(time_in_regeces[0], text, re.IGNORECASE)
            if not match:
                await ctx.send("Invalid interval")
                return
            tinstart = "now"
            tinstrs, input = match.groups()
        start = (datetime.utcnow() + tin2tdelta(tinstart)).timestamp()
        async with self.config.channel(ctx.channel).schedules() as scs:
            scs.append((start, tin2tdelta(tinstrs).seconds, input))
        m = await ctx.send("Schedule created.  I will send a message on my next cycle (10s or less)")
        await asyncio.sleep(5.)
        await m.delete()

    @remindme.command(aliases=["list"])
    async def get(self, ctx):
        """Get a list of all pending reminders"""
        rlist = sorted((await self.config.user(ctx.author).reminders()), key=lambda x: x[0])
        if not rlist:
            await ctx.send(inline("You have no pending reminders!"))
            return
        tz = tzstr_to_tz(await self.config.user(ctx.author).tz())
        o = []
        for c, (timestamp, input) in enumerate(rlist):
            o.append(str(c + 1) + ": " + format_rm_time(datetime.fromtimestamp(float(timestamp)), input, tz))
        o = "```\n" + '\n'.join(o) + "\n```"
        await ctx.send(o)

    @remindme.command(name="remove")
    async def remindme_remove(self, ctx, no: int):
        """Remove a specific pending reminder"""
        rlist = sorted(await self.config.user(ctx.author).reminders(), key=lambda x: x[0])
        if len(rlist) < no:
            await ctx.send(inline("There is no reminder #{}".format(no)))
            return
        async with self.config.user(ctx.author).reminders() as rms:
            rms.remove(rlist[no - 1])
        await ctx.send(inline("Done"))

    @remindme.command()
    async def purge(self, ctx):
        """Delete all pending reminders."""
        await self.config.user(ctx.author).reminders.set([])
        await ctx.send(inline("Done"))


    @commands.group(invoke_without_command=True)
    @checks.mod_or_permissions(administrator=True)
    async def schedule(self, ctx, name, *, text):
        """Sets up a schedule to fire at the specified interval

        [p]schedule name 1d Do something!
        [p]schedule name 5 hours Do something!
        """
        match = re.search(time_in_regeces[0], text, re.IGNORECASE)
        if match:
            tinstart = "now"
            tinstrs, input = match.groups()
        else:
            match = re.search(time_in_regeces[1], text, re.IGNORECASE)
            if not match:
                if name.isdigit() or re.search(time_in_regeces[0], name+" .", re.IGNORECASE):
                    await ctx.send("Invalid interval.  Remember to put 'name' as the first argument.")
                else:
                    await ctx.send_help()
                return
            tinstart, tinstrs, input = match.groups()
        start = (datetime.utcnow() + tin2tdelta(tinstart)).timestamp()

        async with self.config.guild(ctx.guild).schedules() as schedules:
            if name in schedules:
                await ctx.send("There is already a schedule with this name.")
                return
            schedules[name] = {
                "start": start,
                "time": start,
                "end": 2e11,
                "interval": tin2tdelta(tinstrs).seconds,
                "enabled": True,
                "channels": [ctx.channel.id],
                "message": input,
            }
        m = await ctx.send("Schedule created.")
        await asyncio.sleep(5.)
        await m.delete()

    @schedule.command()
    async def begin(self, ctx, name, *, time):
        """Sets the start time for a schedule."""
        time = await self.exact_tartintodt(ctx, time)
        if time is None:
            return
        async with self.config.guild(ctx.guild).schedules() as schedules:
            if name not in schedules:
                await ctx.send("There is no schedule with this name.")
                return
            schedules[name]['start'] = time.timestamp()
            schedules[name]['time'] = time.timestamp()
        await ctx.send(inline("Done."))

    @schedule.command()
    async def end(self, ctx, name, *, time):
        """Sets the end time for a schedule."""
        time = await self.exact_tartintodt(ctx, time)
        if time is None:
            return
        async with self.config.guild(ctx.guild).schedules() as schedules:
            if name not in schedules:
                await ctx.send("There is no schedule with this name.")
                return
            schedules[name]['end'] = time.timestamp()
        await ctx.send(inline("Done."))

    @schedule.command()
    async def interval(self, ctx, name, *, time):
        """Sets the interval for a schedule."""
        if not re.match(exact_tins[0], time):
            await ctx.send("Invalid interval.")
            return
        interval = tin2tdelta(time)
        if interval is None:
            return
        async with self.config.guild(ctx.guild).schedules() as schedules:
            if name not in schedules:
                await ctx.send("There is no schedule with this name.")
                return
            schedules[name]['interval'] = interval.seconds
        await ctx.send(inline("Done."))

    @schedule.command()
    async def message(self, ctx, name, *, message):
        """Sets the message for a schedule."""
        async with self.config.guild(ctx.guild).schedules() as schedules:
            if name not in schedules:
                await ctx.send("There is no schedule with this name.")
                return
            schedules[name]['message'] = message
        await ctx.send(inline("Done."))

    @schedule.group()
    async def channel(self, ctx):
        """Set or remove channels for a schedule."""

    @channel.command()
    async def add(self, ctx, name, channel: discord.TextChannel):
        """Add a channel."""
        async with self.config.guild(ctx.guild).schedules() as schedules:
            if name not in schedules:
                await ctx.send("There is no schedule with this name.")
                return
            if channel.id in schedules[name]['channels']:
                await ctx.send("This channel is already registered.")
                return
            schedules[name]['channels'].append(channel.id)
        await ctx.send(inline("Done"))

    @channel.command(name="remove")
    async def channel_remove(self, ctx, name, channel):
        """Remove a channel."""
        c = bot.get_channel()
        if c is None and channel.isdigit():
            channel_id = channel
        elif c:
            channel_id = channel.id
        else:
            await ctx.send("Invalid channel.")
            return

        async with self.config.guild(ctx.guild).schedules() as schedules:
            if name not in schedules:
                await ctx.send("There is no schedule with this name.")
                return
            if channel_id not in schedules[name]['channels']:
                await ctx.send("This channel is not registered.")
                return
            schedules[name]['channels'].remove(channel_id)
        await ctx.send(inline("Done"))

    @channel.command(name="list")
    async def channel_list(self, ctx, name):
        """List the registered channels."""
        async with self.config.guild(ctx.guild).schedules() as schedules:
            if name not in schedules:
                await ctx.send("There is no schedule with this name.")
                return
            if not schedules[name]['channels']:
                await ctx.send("This schedule has no channels.")
                return
            o = ""
            for c in schedules[name]['channels']:
                ch = self.bot.get_channel(c)
                if ch:
                    o += "{} ({})\n".format(ch.name, c)
                else:
                    o += "deleted-channel ({})\n".format(c)
        for p in pagify(o):
            await ctx.send(box(p))

    @schedule.command()
    async def enable(self, ctx, name):
        """Enable a schedule."""
        async with self.config.guild(ctx.guild).schedules() as schedules:
            if name not in schedules:
                await ctx.send("There is no schedule with this name.")
                return
            schedules[name]['enabled'] = True
        await ctx.send(inline("Done."))

    @schedule.command()
    async def disable(self, ctx, name):
        """Disable a schedule."""
        async with self.config.guild(ctx.guild).schedules() as schedules:
            if name not in schedules:
                await ctx.send("There is no schedule with this name.")
                return
            schedules[name]['enabled'] = False
        await ctx.send(inline("Done."))

    @schedule.command(name="remove")
    async def schedule_remove(self, ctx, name):
        """Remove a schedule."""
        async with self.config.guild(ctx.guild).schedules() as schedules:
            if name not in schedules:
                await ctx.send("There is no schedule with this name.")
                return
            del schedules[name]
        await ctx.send(inline("Deleted schedule {}.".format(name)))

    @schedule.command(name="list")
    async def schedule_list(self, ctx):
        """List the guild's schedules."""
        async with self.config.guild(ctx.guild).schedules() as schedules:
            o = ""
            for n,s in schedules.items():
                o += " - {}{}\n".format(n, " (disabled)" if not s['enabled'] else " (expired)" if s['end'] < datetime.utcnow().timestamp() else "")
                o += "   - Start Time: {}\n".format(datetime.fromtimestamp(s['start']).strftime(SHORT_DT_FORMAT))
                o += "   - Next Time: {}\n".format(datetime.fromtimestamp(s['time']).strftime(SHORT_DT_FORMAT))
                o += "   - End Time: {}\n".format(datetime.fromtimestamp(s['end']).strftime(SHORT_DT_FORMAT))
                o += "   - Interval: {}\n".format(timedelta(seconds=s['interval']))
                o += "   - Message: {}\n".format(s['message'])
        if not o:
            await ctx.send(inline("There are no schedules for this guild."))
        for page in pagify(o):
            await ctx.send(box(page))

    @commands.command(aliases=['settz'])
    async def settimezone(self, ctx, tzstr):
        """Set your timezone."""
        try:
            v = tzstr_to_tz(tzstr)
            await self.config.user(ctx.author).tz.set(tzstr)
            await ctx.send(inline("Set personal timezone to {} ({})".format(str(v), get_tz_name(v))))
        except IOError as e:
            await ctx.send(inline("Invalid tzstr: " + tzstr))

    async def reminderloop(self):
        await self.bot.wait_until_ready()
        async for _ in rpadutils.repeating_timer(10, lambda: self == self.bot.get_cog('TimeCog')):
            urs = await self.config.all_users()
            gds = await self.config.all_guilds()
            now = datetime.utcnow()
            for u in urs:
                for rm in urs[u]['reminders']:
                    if datetime.fromtimestamp(float(rm[0])) < now:
                        async with self.config.user(self.bot.get_user(u)).reminders() as rms:
                            rms.remove(rm)
                        await self.bot.get_user(u).send(rm[1])
            for g in gds:
                for n, sc in gds[g]['schedules'].items():
                    if datetime.fromtimestamp(sc['end']) < now or not sc['enabled']:
                        continue
                    if datetime.fromtimestamp(float(sc['time'])) < now:
                        async with self.config.guild(self.bot.get_guild(g)).schedules() as scs:
                            scs[n]['time'] += scs[n]['interval']
                        for ch in sc['channels']:
                            await self.bot.get_channel(ch).send(sc['message'])

    @commands.command()
    async def time(self, ctx, *, tz: str):
        """Displays the current time in the supplied timezone"""
        try:
            tz_obj = tzstr_to_tz(tz)
        except Exception as e:
            await ctx.send("Failed to parse tz: " + tz)
            return

        now = datetime.now(tz_obj)
        msg = "The time in " + now.strftime('%Z') + " is " + fmt_time_short(now).strip()
        await ctx.send(inline(msg))

    @commands.command()
    async def timeto(self, ctx, tz: str, *, time: str):
        """Compute the time remaining until the [timezone] [time]"""
        try:
            tz_obj = tzstr_to_tz(tz)
        except Exception as e:
            await ctx.send("Failed to parse tz: " + tz)
            return

        try:
            time_obj = timestr_to_time(time)
        except Exception as e:
            await ctx.send("Failed to parse time: " + time)
            return

        now = datetime.now(tz_obj)
        req_time = now.replace(hour=time_obj.tm_hour, minute=time_obj.tm_min)

        if req_time < now:
            req_time = req_time + timedelta(days=1)
        delta = req_time - now

        msg = ("There are " + fmt_hrs_mins(delta.seconds).strip() +
              " until " + time.strip() + " in " + now.strftime('%Z'))
        await ctx.send(inline(msg))

    async def exact_tartintodt(self, ctx, time, allowtat=True):
        user_tz_str = await self.config.user(ctx.author).tz()
        user_timezone = tzstr_to_tz(user_tz_str or 'UTC')

        for ar in exact_tats:
            if not allowtat:
                continue
            match = re.match(ar, time, re.IGNORECASE)
            if not match:
                continue
            match = match.groupdict()

            if not user_tz_str:
                await ctx.send(
                    "Please configure your personal timezone with `{0.clean_prefix}settimezone` first.".format(ctx))
                return

            now = datetime.now(tz=user_timezone)
            defaults = {
                'year': now.year,
                'month': now.month,
                'day': now.day,
                'hour': now.hour,
                'minute': now.minute,
                'merid': 'NONE'
            }
            defaults.update({k: v for k, v in match.items() if v})
            for key in defaults:
                if key not in ['merid']:
                    defaults[key] = int(defaults[key])
            if defaults['merid'] == 'pm' and defaults['hour'] <= 12:
                defaults['hour'] += 12
            elif defaults['merid'] == 'NONE' and defaults['hour'] < now.hour:
                defaults['hour'] += 12
            if defaults['hour'] >= 24:
                defaults['day'] += int(defaults['hour'] // 24)
                defaults['hour'] = defaults['hour'] % 24
            del defaults['merid']
            try:
                rmtime = user_timezone.localize(datetime(**defaults))
            except ValueError as e:
                await ctx.send(inline(str(e).capitalize()))
                return
            if rmtime < now:
                rmtime += timedelta(days=1)
            rmtime = rmtime.astimezone(pytz.utc).replace(tzinfo=None)
            break
        else:
            ir = exact_tins[0]
            match = re.search(ir, time, re.IGNORECASE)
            if not match: # Only use the first one
                raise commands.UserFeedbackCheckFailure("Invalid time string: " + time)
            tinstrs, = match.groups()
            rmtime = datetime.utcnow()
            try:
                rmtime += tin2tdelta(tinstrs)
            except OverflowError:
                raise commands.UserFeedbackCheckFailure(
                    inline("That's way too far in the future!  Please keep it in your lifespan!"))

        return rmtime


def timestr_to_time(timestr):
    timestr = timestr.replace(" ", "")
    try:
        return time.strptime(timestr, "%H:%M")
    except:
        pass
    try:
        return time.strptime(timestr, "%I:%M%p")
    except:
        pass
    try:
        return time.strptime(timestr, "%I%p")
    except:
        pass
    raise commands.UserFeedbackCheckFailure("Invalid Time: " + timestr)


def fmt_hrs_mins(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return '{}hrs {}mins'.format(int(hours), int(minutes))


def fmt_time_short(dt):
    return dt.strftime("%I:%M %p")


def tzstr_to_tz(tz):
    tz = tz.lower().strip()
    if tz in ['edt', 'est', 'et']:
        tz = 'America/New_York'
    elif tz in ['mdt', 'mst', 'mt']:
        tz = 'America/North_Dakota/Center'
    elif tz in ['pdt', 'pst', 'pt']:
        tz = 'America/Los_Angeles'
    elif tz in ['jp', 'jt', 'jst']:
        return tz_lookup['JST']
    elif tz.upper() in tz_lookup:
        return tz_lookup[tz.upper()]
    else:
        for tzo in pytz.all_timezones:
            if tz.lower() in tzo.lower().split("/"):
                tz = tzo
                break
        else:
            for tzo in pytz.all_timezones:
                if tz.lower() in tzo:
                    tz = tzo
                    break
    try:
        return pytz.timezone(tz)
    except Exception as e:
        raise commands.UserFeedbackCheckFailure("Invalid timezone: " + tz)


def tin2tdelta(tinstr):
    if tinstr.lower().strip() == "now":
        return timedelta(0)
    tins = re.findall(r'(-?\d+) ?([a-z]+) ?', tinstr.lower())
    o = timedelta()
    for tin, unit in tins:
        try:
            tin = int(tin)
            if unit[:2] == 'mo':
                o += relativedelta(months=+1)
            elif unit[0] == 'm':
                o += timedelta(minutes=tin)
            elif unit[0] == 'h':
                o += timedelta(hours=tin)
            elif unit[0] == 'd':
                o += timedelta(days=tin)
            elif unit[0] == 'w':
                o += timedelta(weeks=tin)
            elif unit[0] == 'y':
                o += relativedelta(years=+1)
            elif unit[0] == 's':
                raise commands.UserFeedbackCheckFailure(
                    "We aren't exact enough to use seconds! If you need that precision, try this: https://www.timeanddate.com/timer/")
            else:
                raise commands.UserFeedbackCheckFailure(inline(
                    "Invalid unit: {}\nPlease use minutes, hours, days, weeks, months, or, if you're feeling especially zealous, years.".format(
                        unit)))
        except OverflowError:
            raise commands.UserFeedbackCheckFailure(inline("Come on... Be reasonable :/"))
    return o


def ydhm(seconds):
    y, seconds = divmod(seconds, 60 * 60 * 24 * 365)
    d, seconds = divmod(seconds, 60 * 60 * 24)
    h, seconds = divmod(seconds, 60 * 60)
    m, seconds = divmod(seconds, 60)
    y, d, h, m = [int(ydhm) for ydhm in (y, d, h, m)]
    ydhm = []
    if y: ydhm.append("{} yr" .format(y) + ("s" if y > 1 else ''))
    if d: ydhm.append("{} day".format(d) + ("s" if d > 1 else ''))
    if h: ydhm.append("{} hr" .format(h) + ("s" if h > 1 else ''))
    if m: ydhm.append("{} min".format(m) + ("s" if m > 1 else ''))
    return " ".join(ydhm) or "<1 minute"


def format_rm_time(rmtime, input, D_TZ):
    return "'{}' on {} {} ({} from now)".format(
        input,
        D_TZ.fromutc(rmtime).strftime(DT_FORMAT),
        get_tz_name(D_TZ, rmtime),
        ydhm((rmtime - datetime.utcnow()).total_seconds() + 2)
    )


def get_tz_name(tz, dt=None):
    if dt is None:
        dt = datetime.utcnow()
    else:
        dt = dt.replace(tzinfo=None)
    tzname = tz.tzname(datetime(year=dt.year, month=1, day=1))
    tznowname = tz.tzname(dt)
    if tzname != tznowname and tznowname:
        return "{} ({})".format(tzname, tznowname)
    return tzname
