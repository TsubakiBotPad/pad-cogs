import traceback
import asyncio
import re
import datetime
import pytz
from collections import defaultdict
from datetime import timedelta
from enum import Enum

import prettytable
import discord
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import inline, box, pagify

from dadguide import dadguide
from rpadutils import CogSettings

SUPPORTED_SERVERS = ["JP", "NA", "KR", "UK"]


class PadEvents(commands.Cog):
    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.settings = PadEventSettings("padevents")

        # Load event data
        self.events = list()
        self.started_events = set()

        self.fake_uid = -999

    def cog_unload(self):
        # Manually nulling out database because the GC for cogs seems to be pretty shitty
        self.events = list()
        self.started_events = set()

    async def reload_padevents(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('PadEvents'):
            try:
                await self.refresh_data()
                print('Done refreshing PadEvents')
            except Exception as ex:
                print("reload padevents loop caught exception " + str(ex))
                traceback.print_exc()

            await asyncio.sleep(60 * 60 * 1)

    async def refresh_data(self):
        dg_cog = self.bot.get_cog('Dadguide')
        await dg_cog.wait_until_ready()
        scheduled_events = dg_cog.database.get_all_events()

        new_events = []
        for se in scheduled_events:
            try:
                new_events.append(Event(se))
            except Exception as ex:
                print(ex)

        self.events = new_events
        self.started_events = {ev.key for ev in new_events if ev.is_started()}

    async def check_started(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('PadEvents'):
            try:
                events = filter(lambda e: e.is_started() and not e.key in self.started_events, self.events)

                daily_refresh_servers = set()
                for e in events:
                    self.started_events.add(e.key)
                    if e.event_type in [EventType.Guerrilla, EventType.GuerrillaNew, EventType.SpecialWeek]:
                        for gr in list(self.settings.listGuerrillaReg()):
                            if SUPPORTED_SERVERS[e.server_id] == gr['server']:
                                try:
                                    message = box("Server " + SUPPORTED_SERVERS[e.server_id] + ", group " +
                                                  e.groupLongName() + " : " + e.name_and_modifier)
                                    channel = self.bot.get_channel(int(gr['channel_id']))

                                    try:
                                        role_name = '{}_group_{}'.format(
                                            e.server, e.groupLongName())
                                        role = get_role(channel.guild.roles, role_name)
                                        if role and role.mentionable:
                                            message = "{} `: {} is starting`".format(
                                                role.mention, e.name_and_modifier)
                                    except:
                                        pass  # do nothing if role is missing

                                    await channel.send(message)
                                except Exception as ex:
                                    # deregister gr
                                    traceback.print_exc()
                                    #                                     self.settings.removeGuerrillaReg(gr['channel_id'], gr['server'])
                                    print(
                                        "caught exception while sending guerrilla msg" + str(ex))

                    else:
                        if not e.dungeon_type in [DungeonType.Normal]:
                            daily_refresh_servers.add(e.server)

                for server in daily_refresh_servers:
                    msg = self.makeActiveText(server)
                    for daily_registration in list(self.settings.listDailyReg()):
                        try:
                            if server == daily_registration['server']:
                                await self.pageOutput(ctx, msg, channel_id=daily_registration['channel_id'])
                        except Exception as ex:
                            traceback.print_exc()
                            #                             self.settings.removeDailyReg(
                            #                                 daily_registration['channel_id'], daily_registration['server'])
                            print("caught exception while sending daily msg " + str(ex))

            except Exception as ex:
                traceback.print_exc()
                print("caught exception while checking guerrillas " + str(ex))

            try:
                await asyncio.sleep(10)
            except Exception as ex:
                traceback.print_exc()
                print("check event loop caught exception " + str(ex))
                raise ex
        print("done check_started")

    @commands.group()
    @checks.mod_or_permissions(manage_guild=True)
    async def padevents(self, ctx):
        """PAD event tracking"""

    @padevents.command()
    @checks.is_owner()
    async def testevent(self, ctx, server):
        # FIXME: (it's VERY borked)
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        te = dadguide.DgScheduledEvent([], None)
        te.server = server

        te.dungeon_code = 1
        te.event_type = EventType.Guerrilla
        te.event_seq = 0
        self.fake_uid = self.fake_uid - 1
        te.key = self.fake_uid
        te.group = 'F'

        te.open_datetime = datetime.datetime.now(pytz.utc)
        te.close_datetime = te.open_datetime + timedelta(minutes=1)
        te.dungeon_name = 'fake_dungeon_name'
        te.event_modifier = 'fake_event_modifier'
        self.events.append(Event(te))

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
            await ctx.send("Unsupported server, pick one of NA, ~~KR~~, JP")
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
            await ctx.send("Unsupported server, pick one of NA, ~~KR~~, JP")
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
            await ctx.send("Unsupported server, pick one of NA, ~~KR~~, JP")
            return

        channel_id = ctx.channel.id
        if not self.settings.checkDailyReg(channel_id, server):
            await ctx.send("Channel is not active.")
            return

        self.settings.removeDailyReg(channel_id, server)
        await ctx.send("Channel deactivated.")

    @padevents.command(name="listchannels")
    @checks.mod_or_permissions(manage_guild=True)
    async def _listchannel(self, ctx):
        msg = 'Following daily channels are registered:\n'
        msg += self.makeChannelList(self.settings.listDailyReg())
        msg += "\n"
        msg += 'Following guerilla channels are registered:\n'
        msg += self.makeChannelList(self.settings.listGuerrillaReg())
        await self.pageOutput(ctx, msg)

    def makeChannelList(self, reg_list):
        msg = ""
        for cr in reg_list:
            reg_channel_id = cr['channel_id']
            channel = self.bot.get_channel(int(reg_channel_id))
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
                print("page output failed " + str(e))
                print("tried to print: " + page)

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
                events_by_group[e.group].append(e)

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
        """Print upcoming daily events for NA."""
        await self.doPartial(ctx, 'NA')

    @commands.command()
    async def eventsjp(self, ctx):
        """Print upcoming daily events for JP."""
        await self.doPartial(ctx, 'JP')

    @commands.command()
    async def eventskr(self, ctx):
        """Print upcoming daily events for KR."""
        await self.doPartial(ctx, 'KR')

    async def doPartial(self, ctx, server):
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send("Unsupported server, pick one of NA, KR, JP")
            return

        events = EventList(self.events)
        events = events.withServer(server)
        events = events.inType([EventType.Guerrilla, EventType.SpecialWeek])

        active_events = events.activeOnly().itemsByOpenTime(reverse=True)
        pending_events = events.pendingOnly().itemsByOpenTime(reverse=True)

        group_to_active_event = {e.group: e for e in active_events}
        group_to_pending_event = {e.group: e for e in pending_events}

        active_events = list(group_to_active_event.values())
        pending_events = list(group_to_pending_event.values())

        active_events.sort(key=lambda e: e.group, reverse=True)
        pending_events.sort(key=lambda e: e.group, reverse=True)

        if len(active_events) == 0 and len(pending_events) == 0:
            await ctx.send("No events available for " + server)
            return

        output = "Events for {}".format(server)

        if len(active_events) > 0:
            output += "\n\n" + "G Remaining Dungeon"
            for e in active_events:
                output += "\n" + e.toPartialEvent(self)

        if len(pending_events) > 0:
            output += "\n\n" + "G PT    ET    ETA     Dungeon"
            for e in pending_events:
                output += "\n" + e.toPartialEvent(self)

        await ctx.send(box(output))


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
    def __init__(self, scheduled_event: dadguide.DgScheduledEvent):
        self.key = scheduled_event.key()
        self.server = SUPPORTED_SERVERS[scheduled_event.server_id]
        self.open_datetime = scheduled_event.open_datetime
        self.close_datetime = scheduled_event.close_datetime
        self.group = scheduled_event.group_name
        self.dungeon_name = scheduled_event.dungeon.name_na if scheduled_event.dungeon else 'unknown_dungeon'
        self.event_name = '' # scheduled_event.event.name if scheduled_event.event else ''

        self.clean_dungeon_name = cleanDungeonNames(self.dungeon_name)
        self.clean_event_name = self.event_name.replace('!', '').replace(' ', '')

        self.name_and_modifier = self.clean_dungeon_name
        if self.clean_event_name != '':
            self.name_and_modifier += ', ' + self.clean_event_name

        self.event_type = EventType(scheduled_event.event_type_id)
        self.dungeon_type = DungeonType(
            scheduled_event.dungeon.dungeon_type) if scheduled_event.dungeon else DungeonType.Unknown

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
        return self.group.upper()

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
    days = sec // 86400
    sec -= 86400 * days
    hours = sec // 3600
    sec -= 3600 * hours
    minutes = sec // 60

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
