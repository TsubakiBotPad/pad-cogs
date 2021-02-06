from typing import List, TYPE_CHECKING

from padinfo.common.config import UserConfig
from padinfo.core.id import get_monster_by_query, get_id_view_state_data, get_monster_by_id
from padinfo.view_state.base import ViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class IdViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters: List["MonsterModel"],
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=extra_state)
        self.acquire_raw = acquire_raw
        self.alt_monsters = alt_monsters
        self.color = color
        self.base_rarity = base_rarity
        self.transform_base = transform_base
        self.monster = monster
        self.query = query
        self.true_evo_type_raw = true_evo_type_raw

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'query': self.query,
            'resolved_monster_id': self.monster.monster_id,
            'pane_type': 'id',
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']

        # This is to support the 2 vs 1 monster query difference between ^ls and ^id
        query = ims.get('query') or raw_query

        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']

        resolved_monster_id = int(ims.get('resolved_monster_id'))

        monster = await (get_monster_by_id(dgcog, resolved_monster_id)
                         if resolved_monster_id else get_monster_by_query(dgcog, raw_query, user_config.beta_id3))

        transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters = \
            await get_id_view_state_data(dgcog, monster)

        return IdViewState(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                           transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters,
                           extra_state=ims)
