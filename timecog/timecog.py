import asyncio
import re
import time
import traceback
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta

import pytz
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import inline

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

DT_FORMAT = "%A, %b %-d, %Y at %-I:%M %p"


class TimeCog(commands.Cog):
    """Utilities pertaining to time"""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = Config.get_conf(self, identifier=7173306)
        self.config.register_user(reminders=[], tz='')
        self.config.register_channel(schedules=[])

        """
        CONFIG: Config
        |   USERS: Config
        |   |   REMINDERS: list
        |   |   |   REMINDER: tuple
        |   |   |   |   TIME: int (timestamp)
        |   |   |   |   TEXT: str
        |   |   |   |   INTERVAL: Optional[int]
        |   |   TZ: str (tzstr)
        |   CHANNELS: Config
        |   |   SCHEDULES: list
        |   |   |   SCHEDULE: tuple
        |   |   |   |   START: int (timestamp)
        |   |   |   |   INTERVAL: int (seconds)
        |   |   |   |   TEXT: str
        """

        self.bot = bot

    #@commands.group(invoke_without_command=True)
    async def schedule(self, ctx, *, text):
        raise ValueError()
        match = re.search(time_in_regeces[0], text, re.IGNORECASE)
        if match:
            tinstart = "now"
            tinstrs, input = match.groups()
        else:
            match = re.search(time_in_regeces[1], text, re.IGNORECASE)
            if not match:
                await ctx.send("Invalid interval")
                return
            tinstart, tinstrs, input = match.groups()
        start = (datetime.utcnow() + tin2tdelta(tinstart)).timestamp()
        async with self.config.channel(ctx.channel).schedules() as scs:
            scs.append((start, tin2tdelta(tinstrs).seconds, input))
        m = await ctx.send("Schedule created.  I will send a message on my next cycle (10s or less)")
        await asyncio.sleep(5.)
        await m.delete()

    @commands.group(aliases=['remindmeat', 'remindmein'], invoke_without_command=True)
    async def remindme(self, ctx, *, time):
        """Reminds you to do something at a specified time

        [p]remindme 2020-04-13 06:12 Do something!
        [p]remindme 5 weeks Do something!
        [p]remindme 4:13 PM Do something!
        [p]remindme 2020-05-03 Do something!
        [p]remindme 04-13 Do something!
        """
        if time is None:
            return

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
        print(tinstrs, tinstart, input)
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

    @remindme.command()
    async def remove(self, ctx, no: int):
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
            chs = await self.config.all_channels()
            now = datetime.utcnow()
            for u in urs:
                for rm in urs[u]['reminders']:
                    if datetime.fromtimestamp(float(rm[0])) < now:
                        async with self.config.user(self.bot.get_user(u)).reminders() as rms:
                            rms.remove(rm)
                        await self.bot.get_user(u).send(rm[1])
            for c in chs:
                for sc in chs[c]['schedules']:
                    if datetime.fromtimestamp(float(sc[0])) < now:
                        async with self.config.channel(self.bot.get_channel(c)).schedules() as sco:
                            scind = sco.index(sc)
                            sco[scind][0] += sco[scind][1]
                            print(sco, scind, datetime.utcnow())
                        await self.bot.get_channel(c).send(sc[2])

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
