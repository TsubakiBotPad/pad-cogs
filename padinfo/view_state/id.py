from typing import List, TYPE_CHECKING

from padinfo.common.config import UserConfig
from padinfo.core.id import get_id_view_state_data
from padinfo.pane_names import IdMenuPaneNames
from padinfo.view_state.base import ViewState
from padinfo.view_state.common import get_monster_from_ims

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class IdViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters: List["MonsterModel"],
                 use_evo_scroll: bool = True,
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
        self.use_evo_scroll = use_evo_scroll

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': IdMenuPaneNames.id,
            'query': self.query,
            'resolved_monster_id': self.monster.monster_id,
            'use_evo_scroll': str(self.use_evo_scroll),
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        monster = await get_monster_from_ims(dgcog, user_config, ims)
        transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters = \
            await get_id_view_state_data(dgcog, monster)

        raw_query = ims['raw_query']
        # This is to support the 2 vs 1 monster query difference between ^ls and ^id
        query = ims.get('query') or raw_query
        menu_type = ims['menu_type']
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'

        return IdViewState(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                           transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters,
                           use_evo_scroll=use_evo_scroll,
                           extra_state=ims)
