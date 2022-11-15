import datetime
from datetime import timedelta
from typing import Callable, Collection, TYPE_CHECKING

import pytz
from redbot.core.utils.chat_formatting import inline
from tsutils.formatting import normalize_server_name
from tsutils.time import JP_TIMEZONE, KR_TIMEZONE, NA_TIMEZONE

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
        self.open_datetime: datetime.datetime = scheduled_event.open_datetime
        self.close_datetime: datetime.datetime = scheduled_event.close_datetime
        self.dungeon = scheduled_event.dungeon
        self.dungeon_name = self.dungeon.name_en if self.dungeon else 'unknown_dungeon'

        self.clean_dungeon_name = self.dungeon.clean_name_en if self.dungeon else 'unknown_dungeon'

        self.dungeon_type = DungeonType(self.dungeon.dungeon_type) if self.dungeon else DungeonType.Unknown

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

    def start_from_now_sec(self) -> float:
        now = datetime.datetime.now(pytz.utc)
        return (self.open_datetime - now).total_seconds()

    def end_from_now_sec(self) -> float:
        now = datetime.datetime.now(pytz.utc)
        return (self.close_datetime - now).total_seconds()

    def is_started(self):
        """True if past the open time for the event."""
        return self.start_from_now_sec() <= 0

    def is_finished(self):
        """True if past the close time for the event."""
        return self.end_from_now_sec() <= 0

    def start_from_now_discord(self, output_type: str) -> str:
        return f"<t:{int(self.open_datetime.timestamp())}:{output_type}>"

    def end_from_now_discord(self, output_type: str) -> str:
        return f"<t:{int(self.close_datetime.timestamp())}:{output_type}>"

    def end_from_now_full_min(self) -> str:
        days, sec = divmod(self.end_from_now_sec(), 86400)
        hours, sec = divmod(sec, 3600)
        minutes, sec = divmod(sec, 60)

        if days > 0:
            return '{:2}d {:2}h'.format(int(days), int(hours))
        elif hours > 0:
            return '{:2}h {:2}m'.format(int(hours), int(minutes))
        else:
            return '{:2}m'.format(int(minutes))

    def to_partial_event(self, pe, output_type: str):
        ret = inline(self.clean_dungeon_name.ljust(24) + " - ")
        if self.is_started():
            return ret + self.end_from_now_discord(output_type)
        else:
            return ret + self.start_from_now_discord(output_type)

    def __repr__(self):
        return f"Event<{self.clean_dungeon_name} ({self.server})>"


class EventList:
    def __init__(self, event_list: Collection[Event]):
        self.event_list = event_list

    def with_func(self, func: Callable[[Event], bool]) -> "EventList":
        return EventList(list(filter(func, self.event_list)))

    def with_server(self, *servers):
        servers = {normalize_server_name(s) for s in servers}
        return self.with_func(lambda e: e.server in servers)

    def with_type(self, *event_types):
        return self.with_func(lambda e: e.event_type in event_types)

    def with_length(self, *event_lengths):
        return self.with_func(lambda e: e.event_length in event_lengths)

    def with_dungeon_type(self, *dungeon_types):
        return self.with_func(lambda e: e.dungeon_type in dungeon_types)

    def pending_only(self):
        return self.with_func(lambda e: not e.is_started())

    def active_only(self):
        return self.with_func(lambda e: e.is_started() and not e.is_finished())

    def today_only(self, server: str):
        server_timezone = SERVER_TIMEZONES[normalize_server_name(server)]
        today = datetime.datetime.now(server_timezone).date()
        return self.with_func(lambda e: e.open_datetime.astimezone(server_timezone).date() == today)

    def __iter__(self):
        return iter(self.event_list)

    def __bool__(self):
        return bool(self.event_list)
