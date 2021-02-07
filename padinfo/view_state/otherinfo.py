from typing import TYPE_CHECKING

from padinfo.common.config import UserConfig
from padinfo.core.id import get_monster_by_id, get_monster_by_query
from padinfo.pane_names import IdMenuPaneNames
from padinfo.view_state.base import ViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class OtherInfoViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 use_evo_scroll: bool = True,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=extra_state)
        self.color = color
        self.monster = monster
        self.query = query
        self.use_evo_scroll = use_evo_scroll

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': IdMenuPaneNames.otherinfo,
            'query': self.query,
            'resolved_monster_id': self.monster.monster_id,
            'use_evo_scroll': str(self.use_evo_scroll),
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']

        resolved_monster_id = int(ims.get('resolved_monster_id'))

        monster = await (get_monster_by_id(dgcog, resolved_monster_id)
                         if resolved_monster_id else get_monster_by_query(dgcog, raw_query, user_config.beta_id3))

        query = ims.get('query') or raw_query
        menu_type = ims['menu_type']
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'

        return OtherInfoViewState(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                                  use_evo_scroll=use_evo_scroll,
                                  extra_state=ims)
