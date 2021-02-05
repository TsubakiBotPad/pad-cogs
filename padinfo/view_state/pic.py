from typing import TYPE_CHECKING

from padinfo.common.config import UserConfig
from padinfo.core.id import perform_pic_query
from padinfo.view_state.base import ViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class PicViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=extra_state)
        self.color = color
        self.monster = monster
        self.query = query

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'query': self.query,
            'resolved_monster_id': self.monster.monster_id,
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']

        # This is to support the 2 vs 1 monster query difference between ^ls and ^id
        query = ims.get('query') or raw_query

        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']

        monster = await perform_pic_query(dgcog, query, user_config.beta_id3)

        return PicViewState(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                            extra_state=ims)
