import datetime
from datetime import timedelta
from typing import Callable, List, TYPE_CHECKING

import itertools
import pytz
from tsutils.formatting import normalize_server_name
from tsutils.time import JP_TIMEZONE, NA_TIMEZONE, KR_TIMEZONE

from padevents.enums import DungeonType, EventLength

if TYPE_CHECKING:
    from dbcog.models.scheduled_event_model import ScheduledEventModel

SUPPORTED_SERVERS = ["JP", "NA", "KR"]
SERVER_TIMEZONES = {
    "JP": JP_TIMEZONE,
    "NA": NA_TIMEZONE,
    "KR": KR_TIMEZONE,
}


class Event:
    def __init__(self, scheduled_event: "ScheduledEventModel"):
        self.key = scheduled_event.event_id
        self.server = SUPPORTED_SERVERS[scheduled_event.server_id]
        self.open_datetime = scheduled_event.open_datetime
        self.close_datetime = scheduled_event.close_datetime
        self.group = scheduled_event.group_name
        self.dungeon = scheduled_event.dungeon
        self.dungeon_name = self.dungeon.name_en if self.dungeon else 'unknown_dungeon'
        self.event_name = ''

        self.clean_dungeon_name = self.dungeon.clean_name_en if self.dungeon else 'unknown_dungeon'
        self.clean_event_name = self.event_name.replace('!', '').replace(' ', '')

        self.name_and_modifier = self.clean_dungeon_name
        if self.clean_event_name != '':
            self.name_and_modifier += ', ' + self.clean_event_name

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

    @property
    def event_length(self) -> EventLength:
        # This is a little off.  I don't know how exact these things are.
        length = self.close_datetime - self.open_datetime
        if length > timedelta(days=8):
            return EventLength.special
        if length > timedelta(days=2):
            return EventLength.weekly
        if length > timedelta(hours=20):
            return EventLength.daily
        return EventLength.limited

    def tostr(self):
        return self.open_datetime.strftime("%Y-%m-%d %H:%M") + "," + self.close_datetime.strftime("%Y-%m-%d %H:%M") \
               + "," + self.group + "," + self.dungeon_name

    def start_pst(self):
        tz = pytz.timezone('US/Pacific')
        return self.open_datetime.astimezone(tz)

    def start_est(self):
        tz = pytz.timezone('US/Eastern')
        return self.open_datetime.astimezone(tz)

    def start_from_now(self):
        return f'{self.start_from_now_sec() // 3600:2}h' \
               f' {(self.start_from_now_sec() % 3600) // 60:2}m'

    def end_from_now(self):
        return f'{self.end_from_now_sec() // 3600:2}h' \
               f' {(self.end_from_now_sec() % 3600) // 60:2}m'

    def end_from_now_full_min(self):
        days, sec = divmod(self.end_from_now_sec(), 86400)
        hours, sec = divmod(sec, 3600)
        minutes, sec = divmod(sec, 60)

        if days > 0:
            return '{:2}d {:2}h'.format(int(days), int(hours))
        elif hours > 0:
            return '{:2}h {:2}m'.format(int(hours), int(minutes))
        else:
            return '{:2}m'.format(int(minutes))

    def to_guerrilla_str(self):
        return self.start_pst().strftime("%H:%M")

    def to_date_str(self):
        return self.server + "," + self.group + "," + self.start_pst().strftime("%Y-%m-%d %H:%M") + "," + \
               self.start_est().strftime("%Y-%m-%d %H:%M") + "," + self.start_from_now()

    def group_short_name(self):
        return self.group.upper().replace('RED', 'R').replace('BLUE', 'B').replace('GREEN', 'G')

    def group_long_name(self):
        return self.group.upper() if self.group is not None else "UNGROUPED"

    def to_partial_event(self, pe):
        group = self.group_short_name()
        if self.is_started():
            return group + " " + self.end_from_now() + "   " + self.name_and_modifier
        else:
            return group + " " + self.start_pst().strftime("%H:%M") + " " + self.start_est().strftime("%H:%M") \
                   + " " + self.start_from_now() + " " + self.name_and_modifier


class EventList:
    def __init__(self, event_list: List[Event]):
        self.event_list = event_list

    def with_func(self, func: Callable[[Event], bool], exclude=False):
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

    def with_length(self, event_length):
        return self.with_func(lambda e: e.event_length == event_length)

    def in_length(self, event_lengths):
        return self.with_func(lambda e: e.event_length in event_lengths)

    def with_dungeon_type(self, dungeon_type, exclude=False):
        return self.with_func(lambda e: e.dungeon_type == dungeon_type, exclude)

    def in_dungeon_type(self, dungeon_types, exclude=False):
        return self.with_func(lambda e: e.dungeon_type in dungeon_types, exclude)

    def is_grouped(self, exclude=False):
        return self.with_func(lambda e: e.group is not None, exclude)

    def with_name_contains(self, name, exclude=False):
        return self.with_func(lambda e: name.lower() in e.dungeon_name.lower(), exclude)

    def started_only(self):
        return self.with_func(lambda e: e.is_started())

    def pending_only(self):
        return self.with_func(lambda e: e.is_pending())

    def active_only(self):
        return self.with_func(lambda e: e.is_active())

    def available_only(self):
        return self.with_func(lambda e: e.is_available())

    def today_only(self, server: str):
        server_timezone = SERVER_TIMEZONES[normalize_server_name(server)]
        today = datetime.datetime.now(server_timezone).day
        return self.with_func(lambda e: e.open_datetime.astimezone(server_timezone).day == today)

    def items_by_open_time(self, reverse=False):
        return list(sorted(self.event_list, key=(lambda e: (e.open_datetime, e.dungeon_name)), reverse=reverse))

    def items_by_close_time(self, reverse=False):
        return list(sorted(self.event_list, key=(lambda e: (e.close_datetime, e.dungeon_name)), reverse=reverse))

    def __iter__(self):
        return iter(self.event_list)

    def __bool__(self):
        return bool(self.event_list)
