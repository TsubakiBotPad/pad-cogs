from typing import List, TYPE_CHECKING, Optional

from padinfo.common.config import UserConfig
from padinfo.common.external_links import ilmina_skill
from padinfo.pane_names import IdMenuPaneNames
from padinfo.view_state.base import ViewState
from padinfo.view_state.common import get_monster_from_ims, get_reaction_list_from_ims

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class MaterialsViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 mats: List["MonsterModel"], usedin: List["MonsterModel"], gemid: Optional[str],
                 gemusedin: List["MonsterModel"], skillups: List["MonsterModel"], skillup_evo_count: int, link: str,
                 gem_override: bool,
                 use_evo_scroll: bool = True,
                 reaction_list: List[str] = None,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=extra_state)
        self.reaction_list = reaction_list
        self.link = link
        self.skillup_evo_count = skillup_evo_count
        self.skillups = skillups
        self.gemusedin = gemusedin
        self.mats = mats
        self.usedin = usedin
        self.gemid = gemid
        self.gem_override = gem_override
        self.query = query
        self.monster = monster
        self.color = color
        self.use_evo_scroll = use_evo_scroll

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': IdMenuPaneNames.materials,
            'query': self.query,
            'resolved_monster_id': self.monster.monster_id,
            'use_evo_scroll': str(self.use_evo_scroll),
            'reaction_list': ','.join(self.reaction_list) if self.reaction_list else None,
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):

        monster = await get_monster_from_ims(dgcog, user_config, ims)
        mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, stackable = \
            await MaterialsViewState.query(dgcog, monster)

        if mats is None:
            return None

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        menu_type = ims['menu_type']
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        reaction_list = get_reaction_list_from_ims(ims)

        return MaterialsViewState(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                                  mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, stackable,
                                  use_evo_scroll=use_evo_scroll,
                                  reaction_list=reaction_list,
                                  extra_state=ims)

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
        gem_override = False

        if not any([mats, usedin, gemusedin, skillups and not monster.is_stackable]):
            return None, None, None, None, None, None, None, None
        if not any([mats, usedin, skillups and not monster.is_stackable]):
            mats, gemusedin, _, usedin, skillups, skillup_evo_count, link, _ \
                = await MaterialsViewState.query(dgcog, evo_gem)
            gem_override = True

        return mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, gem_override
