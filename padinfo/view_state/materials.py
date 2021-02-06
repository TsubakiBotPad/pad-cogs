from typing import List, TYPE_CHECKING, Optional

from padinfo.common.config import UserConfig
from padinfo.common.external_links import ilmina_skill
from padinfo.core.id import get_monster_by_id, get_monster_by_query
from padinfo.view_state.base import ViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class MaterialsViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 mats: List["MonsterModel"], usedin: List["MonsterModel"], gemid: Optional[str],
                 gemusedin: List["MonsterModel"], skillups: List["MonsterModel"], skillup_evo_count: int, link: str,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=extra_state)
        self.link = link
        self.skillup_evo_count = skillup_evo_count
        self.skillups = skillups
        self.gemusedin = gemusedin
        self.mats = mats
        self.usedin = usedin
        self.gemid = gemid
        self.query = query
        self.monster = monster
        self.color = color

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'query': self.query,
            'resolved_monster_id': self.monster.monster_id,
            'pane_type': 'materials',
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']

        original_author_id = ims['original_author_id']

        menu_type = ims['menu_type']

        query = ims.get('query') or raw_query

        resolved_monster_id = int(ims.get('resolved_monster_id'))

        monster = await (get_monster_by_id(dgcog, resolved_monster_id)
                         if resolved_monster_id else get_monster_by_query(dgcog, raw_query, user_config.beta_id3))

        mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link = await MaterialsViewState.query(dgcog, monster)

        return MaterialsViewState(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                                  mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, extra_state=ims)

    @staticmethod
    async def query(dgcog, monster):
        db_context = dgcog.database
        mats = db_context.graph.evo_mats_by_monster(monster)
        usedin = db_context.graph.material_of_monsters(monster)
        evo_gem = db_context.graph.evo_gem_monster(monster)
        gemid = str(evo_gem.monster_no_na) if evo_gem else None
        gemusedin = db_context.graph.material_of_monsters(evo_gem) if evo_gem else []
        skillups = []
        skillup_evo_count = 0
        link = ilmina_skill(monster)

        if monster.active_skill:
            sums = [m for m in db_context.get_monsters_by_active(monster.active_skill.active_skill_id)
                    if db_context.graph.monster_is_farmable_evo(m)]
            sugs = [db_context.graph.evo_gem_monster(su) for su in sums]
            vsums = []
            for su in sums:
                if not any(susu in vsums for susu in db_context.graph.get_alt_monsters(su)):
                    vsums.append(su)
            skillups = [su for su in vsums
                        if db_context.graph.monster_is_farmable_evo(su) and
                        db_context.graph.get_base_id(su) != db_context.graph.get_base_id(monster) and
                        su not in sugs] if monster.active_skill else []
            skillup_evo_count = len(sums) - len(vsums)

        if not any([mats, usedin, gemusedin, skillups and not monster.is_stackable]):
            return None, None, None, None, None, None, None, None

        return mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link
