from .base_model import BaseModel
from .dungeon_model import DungeonModel
from datetime import datetime
import pytz


class ScheduledEventModel(BaseModel):
    def __init__(self, **kwargs):
        self.event_id = kwargs["event_id"]
        self.server_id = kwargs.get("server_id")
        self.event_type_id = kwargs.get("event_type_id")
        self.start_timestamp = kwargs.get("start_timestamp")
        self.end_timestamp = kwargs.get("end_timestamp")
        self.message = kwargs.get("message")
        self.url = kwargs.get("url")

        self.dungeon: DungeonModel = kwargs.get("dungeon_model")
        self.dungeon_id = kwargs.get("dungeon_id")
        self.sub_dungeon_id = kwargs.get("sub_dungeon_id")

    @property
    def open_datetime(self) -> datetime:
        return datetime.utcfromtimestamp(self.start_timestamp).replace(tzinfo=pytz.UTC)

    @open_datetime.setter
    def open_datetime(self, value: datetime):
        self.start_timestamp = int(value.timestamp())

    @property
    def close_datetime(self) -> datetime:
        return datetime.utcfromtimestamp(self.end_timestamp).replace(tzinfo=pytz.UTC)

    @close_datetime.setter
    def close_datetime(self, value: datetime):
        self.end_timestamp = int(value.timestamp())

    def to_dict(self):
        return {
            'dungeon_id': self.dungeon_id,
        }
