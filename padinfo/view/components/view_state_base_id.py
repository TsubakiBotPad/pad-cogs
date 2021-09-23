from typing import TYPE_CHECKING, List

from discordmenu.embed.view_state import ViewState
from tsutils.enums import AltEvoSort
from tsutils.query_settings import QuerySettings

from padinfo.common.config import UserConfig
from padinfo.view.common import get_monster_from_ims
from padinfo.view.components.evo_scroll_mixin import EvoScrollViewState, MonsterEvolution

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class ViewStateBaseId(ViewState, EvoScrollViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 alt_monsters: List[MonsterEvolution], is_jp_buffed: bool, query_settings: QuerySettings,
                 reaction_list: List[str] = None,
                 extra_state=None):
        super().__init__(original_author_id=original_author_id, menu_type=menu_type, raw_query=raw_query,
                         extra_state=extra_state)
        self.dfs_alt_monsters = alt_monsters
        self.reaction_list = reaction_list
        self.color = color
        self.monster = monster
        self.is_jp_buffed = is_jp_buffed
        self.query = query
        self.query_settings = query_settings

        if self.query_settings.evosort == AltEvoSort.dfs:
            self.alt_monsters = self.dfs_alt_monsters
        else:
            self.alt_monsters = sorted(self.dfs_alt_monsters, key=lambda m: m.monster.monster_id)

        self.alt_monster_ids = [m.monster.monster_id for m in self.alt_monsters]

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'query': self.query,
            'query_settings': self.query_settings.serialize(),
            'resolved_monster_id': self.monster.monster_id,
            'reaction_list': self.reaction_list,
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        monster = await get_monster_from_ims(dbcog, ims)

        alt_monsters = cls.get_alt_monsters_and_evos(dbcog, monster)

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        query_settings = QuerySettings.deserialize(ims.get('query_settings'))
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)

        return cls(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                   alt_monsters, is_jp_buffed, query_settings,
                   reaction_list=reaction_list,
                   extra_state=ims)
