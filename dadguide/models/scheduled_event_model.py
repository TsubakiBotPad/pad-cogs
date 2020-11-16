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
        self.group_name = kwargs.get("group_name")

        self.dungeon: DungeonModel = kwargs.get("dungeon_model")
        self.dungeon_id = self.dungeon.dungeon_id if self.dungeon else None

    def key(self):
        """
        This is just here for compatibility and will be deleted
        """
        return self.event_id

    @property
    def open_datetime(self):
        return datetime.utcfromtimestamp(self.start_timestamp).replace(tzinfo=pytz.UTC)

    @open_datetime.setter
    def open_datetime(self, value):
        self.start_timestamp = int(value.timestamp())

    @property
    def close_datetime(self):
        return datetime.utcfromtimestamp(self.end_timestamp).replace(tzinfo=pytz.UTC)

    @close_datetime.setter
    def close_datetime(self, value):
        self.end_timestamp = int(value.timestamp())

    def to_dict(self):
        return {
            'dungeon_id': self.event_id,
        }
