from typing import List, TYPE_CHECKING

from padinfo.common.config import UserConfig
from padinfo.core.id import get_id_view_state_data
from padinfo.pane_names import IdMenuPaneNames
from padinfo.view_state.base_id import ViewStateBaseId
from padinfo.view_state.common import get_monster_from_ims, get_reaction_list_from_ims

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class IdViewState(ViewStateBaseId):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters: List["MonsterModel"],
                 use_evo_scroll: bool = True,
                 reaction_list: List[str] = None,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, query, color, monster,
                         use_evo_scroll=use_evo_scroll,
                         reaction_list=reaction_list,
                         extra_state=extra_state)
        self.acquire_raw = acquire_raw
        self.alt_monsters = alt_monsters
        self.base_rarity = base_rarity
        self.transform_base = transform_base
        self.true_evo_type_raw = true_evo_type_raw

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': IdMenuPaneNames.id,
        })
        return ret

    @classmethod
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict):
        monster = await get_monster_from_ims(dgcog, ims)
        transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters = \
            await get_id_view_state_data(dgcog, monster)

        raw_query = ims['raw_query']
        # This is to support the 2 vs 1 monster query difference between ^ls and ^id
        query = ims.get('query') or raw_query
        menu_type = ims['menu_type']
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        reaction_list = get_reaction_list_from_ims(ims)

        return cls(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                   transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters,
                   use_evo_scroll=use_evo_scroll,
                   reaction_list=reaction_list,
                   extra_state=ims)
