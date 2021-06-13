from typing import TYPE_CHECKING, List, NamedTuple, Optional

from discordmenu.embed.view_state import ViewState
from tsutils.enums import AltEvoSort
from tsutils.query_settings import QuerySettings

from padinfo.common.config import UserConfig
from padinfo.view.common import get_monster_from_ims

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel
    from dadguide.models.evolution_model import EvolutionModel
    from dadguide.database_context import DbContext


class MonsterEvolution(NamedTuple):
    monster: "MonsterModel"
    evolution: Optional["EvolutionModel"]


class ViewStateBaseId(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 alt_monsters: List[MonsterEvolution], is_jp_buffed: bool, query_settings: QuerySettings,
                 use_evo_scroll: bool = True,
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
        self.use_evo_scroll = use_evo_scroll

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
            'use_evo_scroll': str(self.use_evo_scroll),
            'reaction_list': self.reaction_list,
        })
        return ret

    @classmethod
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        monster = await get_monster_from_ims(dgcog, ims)

        alt_monsters = cls.get_alt_monsters_and_evos(dgcog, monster)

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        query_settings = QuerySettings.deserialize(ims.get('query_settings'))
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')
        is_jp_buffed = dgcog.database.graph.monster_is_discrepant(monster)

        return cls(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                   alt_monsters, is_jp_buffed, query_settings,
                   use_evo_scroll=use_evo_scroll,
                   reaction_list=reaction_list,
                   extra_state=ims)

    @classmethod
    def get_alt_monsters_and_evos(cls, dgcog, monster) -> List[MonsterEvolution]:
        graph = dgcog.database.graph
        alt_monsters = graph.get_alt_monsters(monster)
        return [MonsterEvolution(m, graph.get_evolution(m)) for m in alt_monsters]

    def decrement_monster(self, dgcog, ims: dict):
        db_context: "DbContext" = dgcog.database
        if self.use_evo_scroll:
            index = self.alt_monster_ids.index(self.monster.monster_id)
            prev_monster_id = self.alt_monster_ids[index - 1]
        else:
            prev_monster = db_context.graph.numeric_prev_monster(self.monster)
            prev_monster_id = prev_monster.monster_id if prev_monster else None
            if prev_monster_id is None:
                ims['unsupported_transition'] = True
        ims['resolved_monster_id'] = str(prev_monster_id)

    def increment_monster(self, dgcog, ims: dict):
        db_context: "DbContext" = dgcog.database
        if self.use_evo_scroll:
            index = self.alt_monster_ids.index(self.monster.monster_id)
            if index == len(self.alt_monster_ids) - 1:
                # cycle back to the beginning of the evos list
                next_monster_id = self.alt_monster_ids[0]
            else:
                next_monster_id = self.alt_monster_ids[index + 1]
        else:
            next_monster = db_context.graph.numeric_next_monster(self.monster)
            next_monster_id = next_monster.monster_id if next_monster else None
            if next_monster_id is None:
                ims['unsupported_transition'] = True
        ims['resolved_monster_id'] = str(next_monster_id)
