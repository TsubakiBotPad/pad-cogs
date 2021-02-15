from typing import List

from padinfo.common.config import UserConfig
from padinfo.view_state.base import ViewStateBase


class MessageViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query,
                 color, message,
                 reaction_list: List[str] = None):
        super().__init__(original_author_id, menu_type, raw_query, reaction_list=reaction_list)
        self.message = message
        self.color = color

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        return MessageViewState('', '', '', user_config.color, ims.get('message'),
                                reaction_list=ims.get('reaction_list'))
