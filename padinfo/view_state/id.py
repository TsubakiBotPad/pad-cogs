from typing import List, TYPE_CHECKING

from padinfo.common.config import UserConfig
from padinfo.core.id import perform_id_query
from padinfo.view_state.base import ViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class IdViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, monster: "MonsterModel", color,
                 is_transform_base,
                 true_evo_type_raw, acquire_raw, base_rarity, alt_monsters: List["MonsterModel"], extra_state=None):
        self.extra_state = extra_state
        self.query = query
        self.base_rarity = base_rarity
        self.acquire_raw = acquire_raw
        self.monster = monster
        self.menu_type = menu_type
        self.original_author_id = original_author_id
        self.raw_query = raw_query
        self.is_transform_base = is_transform_base
        self.true_evo_type_raw = true_evo_type_raw
        self.alt_monsters = alt_monsters
        self.color = color

    def serialize(self):
        ret = {
            'raw_query': self.raw_query,
            'query': self.query,
            'menu_type': self.menu_type,
            'original_author_id': self.original_author_id,
            'resolved_monster_id': self.monster.monster_id,
        }
        ret.update(self.extra_state)
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']

        # This is to support the 2 vs 1 monster query difference between ^ls and ^id
        query = ims.get('query') or raw_query

        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']

        monster, is_transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters = \
            await perform_id_query(dgcog, query, user_config.beta_id3)

        return IdViewState(original_author_id, menu_type, raw_query, query, monster, user_config.color,
                           is_transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters,
                           extra_state=ims)
