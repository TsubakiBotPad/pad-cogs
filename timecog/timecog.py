import time
from datetime import timedelta

import pytz
from redbot.core import commands
from redbot.core.utils.chat_formatting import *

tz_lookup = dict([(pytz.timezone(x).localize(datetime.datetime.now()).tzname(), pytz.timezone(x))
                  for x in pytz.all_timezones])


class TimeCog(commands.Cog):
    """Utilities to convert time"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    @commands.command()
    async def time(self, ctx, *, tz: str):
        """Displays the current time in the supplied timezone"""
        try:
            tz_obj = tzStrToObj(tz)
        except Exception as e:
            await ctx.send("Failed to parse tz: " + tz)
            return

        now = datetime.datetime.now(tz_obj)
        msg = "The time in " + now.strftime('%Z') + " is " + fmtTimeShort(now).strip()
        await ctx.send(inline(msg))

    @commands.command()
    async def timeto(self, ctx, tz: str, *, time: str):
        """Compute the time remaining until the [timezone] [time]"""
        try:
            tz_obj = tzStrToObj(tz)
        except Exception as e:
            await ctx.send("Failed to parse tz: " + tz)
            return

        try:
            time_obj = timeStrToObj(time)
        except Exception as e:
            print(e)
            await ctx.send("Failed to parse time: " + time)
            return

        now = datetime.datetime.now(tz_obj)
        req_time = now.replace(hour=time_obj.tm_hour, minute=time_obj.tm_min)

        if req_time < now:
            req_time = req_time + timedelta(days=1)
        delta = req_time - now

        msg = "There are " + fmtHrsMins(delta.seconds).strip() + \
              " until " + time.strip() + " in " + now.strftime('%Z')
        await ctx.send(inline(msg))


def timeStrToObj(timestr):
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
    raise Exception()


def fmtHrsMins(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return '{:2}hrs {:2}mins'.format(int(hours), int(minutes))


def fmtTimeShort(dt):
    return dt.strftime("%I:%M %p")


def tzStrToObj(tz):
    tz = tz.lower().strip()
    if tz in ['edt', 'est', 'et']:
        tz = 'America/New_York'
    elif tz in ['mdt', 'mst', 'mt']:
        tz = 'America/North_Dakota'
    elif tz in ['pdt', 'pst', 'pt']:
        tz = 'America/Los_Angeles'
    elif tz in ['jp', 'jt', 'jst']:
        return tz_lookup['JST']
    else:
        return tz_lookup[tz.upper()]

    tz_obj = pytz.timezone(tz)
    return tz_obj
