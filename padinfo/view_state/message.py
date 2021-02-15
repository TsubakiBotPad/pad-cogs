from typing import List

from padinfo.common.config import UserConfig
from padinfo.view_state.base import ViewStateBase


class MessageViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query,
                 color, message,
                 reaction_list: List[str] = None):
        super().__init__(original_author_id, menu_type, raw_query, reaction_list=reaction_list)
        print('self.menu_type', menu_type)
        self.message = message
        self.color = color

    @classmethod
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict):
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        raw_query = ims.get('raw_query')
        return cls(original_author_id, menu_type, raw_query, user_config.color, ims.get('message'),
                   reaction_list=ims.get('reaction_list'))
