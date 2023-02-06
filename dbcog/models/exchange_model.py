import re
from datetime import datetime

from tsutils.enums import Server

from .base_model import BaseModel


class ExchangeModel(BaseModel):
    def __init__(self, **kwargs):
        self.trade_id = kwargs['trade_id']
        self.server = Server(('JP', 'NA', 'KR')[kwargs['server_id']])
        self.target_monster_id = kwargs['target_monster_id']
        self.required_monster_ids = [int(i) for i in re.findall(r'\d+', kwargs['required_monster_ids'])]
        self.required_count = kwargs['required_count']
        self.start_timestamp = datetime.fromtimestamp(kwargs['start_timestamp'])
        self.end_timestamp = datetime.fromtimestamp(kwargs['end_timestamp'])
        self.permanent = bool(kwargs['permanent'])
        self.menu_idx = kwargs['menu_idx']
        self.order_idx = kwargs['order_idx']
        self.flags = kwargs['flags']
        self.tstamp = datetime.fromtimestamp(kwargs['tstamp'])

    def to_dict(self):
        return {
            'from': self.required_monster_ids,
            'to': self.target_monster_id,
        }
