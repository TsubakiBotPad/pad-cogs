from typing import TYPE_CHECKING, List, NamedTuple, Optional

from discordmenu.embed.view_state import ViewState
from tsutils.query_settings import QuerySettings

from padinfo.common.config import UserConfig
from padinfo.view.common import get_monster_from_ims

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel
    from dadguide.models.evolution_model import EvolutionModel


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
        self.alt_monsters = alt_monsters
        self.reaction_list = reaction_list
        self.color = color
        self.monster = monster
        self.is_jp_buffed = is_jp_buffed
        self.query = query
        self.query_settings = query_settings
        self.use_evo_scroll = use_evo_scroll

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
