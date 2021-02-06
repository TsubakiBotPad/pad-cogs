from typing import TYPE_CHECKING, List

from padinfo.common.config import UserConfig
from padinfo.core.id import perform_pantheon_query
from padinfo.view_state.base import ViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class PantheonViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 pantheon_list: List["MonsterModel"], series_name: str,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=extra_state)
        self.series_name = series_name
        self.pantheon_list = pantheon_list
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

        monster, pantheon_list, series_name = await perform_pantheon_query(dgcog, query, user_config.beta_id3)

        return PantheonViewState(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                            pantheon_list, series_name,
                            extra_state=ims)
