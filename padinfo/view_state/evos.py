from typing import List, TYPE_CHECKING

from padinfo.common.config import UserConfig
from padinfo.core.id import perform_evos_query
from padinfo.view_state.base import ViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class EvosViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 alt_versions: List["MonsterModel"], gem_versions: List["MonsterModel"],
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=extra_state)
        self.alt_versions = alt_versions
        self.gem_versions = gem_versions
        self.query = query
        self.monster = monster
        self.color = color

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'query': self.query,
            'resolved_monster_id': self.monster.monster_id
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']

        original_author_id = ims['original_author_id']

        menu_type = ims['menu_type']

        query = ims.get('query') or raw_query

        monster, alt_versions, gem_versions = await perform_evos_query(dgcog, query, user_config.beta_id3)

        return EvosViewState(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                   alt_versions, gem_versions, extra_state=ims)
