from typing import List, TYPE_CHECKING

from padinfo.common.config import UserConfig
from padinfo.pane_names import IdMenuPaneNames
from padinfo.view_state.base import ViewState
from padinfo.view_state.common import get_monster_from_ims

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class EvosViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 alt_versions: List["MonsterModel"], gem_versions: List["MonsterModel"],
                 use_evo_scroll: bool = True,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=extra_state)
        self.alt_versions = alt_versions
        self.gem_versions = gem_versions
        self.query = query
        self.monster = monster
        self.color = color
        self.use_evo_scroll = use_evo_scroll

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': IdMenuPaneNames.evos,
            'query': self.query,
            'resolved_monster_id': self.monster.monster_id,
            'use_evo_scroll': str(self.use_evo_scroll),
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        monster = await get_monster_from_ims(dgcog, user_config, ims)
        alt_versions, gem_versions = await EvosViewState.query(dgcog, monster)

        if alt_versions is None:
            return None
        print('def not kittens')

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        menu_type = ims['menu_type']

        return EvosViewState(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                             alt_versions, gem_versions,
                             use_evo_scroll=use_evo_scroll,
                             extra_state=ims)

    @staticmethod
    async def query(dgcog, monster):
        db_context = dgcog.database
        alt_versions = sorted({*db_context.graph.get_alt_monsters_by_id(monster.monster_no)},
                              key=lambda x: x.monster_id)
        gem_versions = list(filter(None, map(db_context.graph.evo_gem_monster, alt_versions)))
        if len(alt_versions) == 1 and len(gem_versions) == 0:
            return None, None
        return alt_versions, gem_versions
