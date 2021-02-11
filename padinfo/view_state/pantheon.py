from typing import TYPE_CHECKING, List

from padinfo.common.config import UserConfig
from padinfo.pane_names import IdMenuPaneNames
from padinfo.view_state.base import ViewState
from padinfo.view_state.common import get_monster_from_ims, get_reaction_list_from_ims

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class PantheonViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 pantheon_list: List["MonsterModel"], series_name: str,
                 use_evo_scroll: bool = True,
                 reaction_list: List[str] = None,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=extra_state)
        self.reaction_list = reaction_list
        self.series_name = series_name
        self.pantheon_list = pantheon_list
        self.color = color
        self.monster = monster
        self.query = query
        self.use_evo_scroll = use_evo_scroll

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': IdMenuPaneNames.pantheon,
            'query': self.query,
            'resolved_monster_id': self.monster.monster_id,
            'use_evo_scroll': str(self.use_evo_scroll),
            'reaction_list': ','.join(self.reaction_list) if self.reaction_list else None,
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        monster = await get_monster_from_ims(dgcog, user_config, ims)
        pantheon_list, series_name = await PantheonViewState.query(dgcog, monster)

        if pantheon_list is None:
            return None

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        menu_type = ims['menu_type']
        reaction_list = get_reaction_list_from_ims(ims)

        return PantheonViewState(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                                 pantheon_list, series_name,
                                 use_evo_scroll=use_evo_scroll,
                                 reaction_list=reaction_list,
                                 extra_state=ims)

    @staticmethod
    async def query(dgcog, monster):
        db_context = dgcog.database
        full_pantheon = db_context.get_monsters_by_series(monster.series_id)
        if not full_pantheon:
            return None, None
        pantheon_list = list(filter(lambda x: db_context.graph.monster_is_base(x), full_pantheon))
        if len(pantheon_list) == 0 or len(pantheon_list) > 20:
            return None, None

        series_name = monster.series.name_en

        return pantheon_list, series_name
