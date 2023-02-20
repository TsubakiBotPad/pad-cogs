from typing import List, Optional, TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedField
from discordmenu.embed.text import LinkedText
from tsutils.menu.components.config import UserConfig
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.common import get_monster_from_ims
from padinfo.view.components.evo_scroll_mixin import EvoScrollView, MonsterEvolution
from padinfo.view.components.view_state_base_id import ViewStateBaseId, IdBaseView

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel

MAX_MONS_TO_SHOW = 5


class MaterialsViewState(ViewStateBaseId):
    def __init__(self, original_author_id, menu_type, raw_query, query, qs: QuerySettings,
                 monster: "MonsterModel",
                 alt_monsters: List[MonsterEvolution], is_jp_buffed: bool,
                 mats: List["MonsterModel"], usedin: List["MonsterModel"], gemid: Optional[str],
                 gemusedin: List["MonsterModel"], skillups: List["MonsterModel"], skillup_evo_count: int, link: str,
                 gem_override: bool,
                 reaction_list: List[str] = None,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, query, qs, monster,
                         alt_monsters, is_jp_buffed,
                         reaction_list=reaction_list,
                         extra_state=extra_state)
        self.reaction_list = reaction_list
        self.link = link
        self.skillup_evo_count = skillup_evo_count
        self.skillups = skillups
        self.gemusedin = gemusedin
        self.mats = mats
        self.usedin = usedin
        self.gemid = gemid
        self.gem_override = gem_override

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': MaterialsView.VIEW_TYPE,
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        monster = await get_monster_from_ims(dbcog, ims)
        mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, stackable = \
            await MaterialsViewState.do_query(dbcog, monster)

        if mats is None:
            return None

        alt_monsters = cls.get_alt_monsters_and_evos(dbcog, monster)
        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        qs = QuerySettings.deserialize(ims.get('qs'))
        menu_type = ims['menu_type']
        original_author_id = ims['original_author_id']
        reaction_list = ims.get('reaction_list')
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)

        return cls(original_author_id, menu_type, raw_query, query, qs, monster,
                   alt_monsters, is_jp_buffed,
                   mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, stackable,
                   reaction_list=reaction_list,
                   extra_state=ims)

    @staticmethod
    async def do_query(dbcog, monster):
        db_context = dbcog.database
        mats = db_context.graph.evo_mats(monster)
        usedin = db_context.graph.material_of_monsters(monster)
        evo_gem = db_context.graph.evo_gem_monster(monster)
        gemid = str(evo_gem.monster_no_na) if evo_gem else None
        gemusedin = db_context.graph.material_of_monsters(evo_gem) if evo_gem else []
        skillups = []
        skillup_evo_count = 0
        link = MonsterLink.ilmina(monster)

        if monster.active_skill:
            sums = [m for m in db_context.get_monsters_by_active(
                monster.active_skill.active_skill_id,
                server=monster.server_priority)
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
                = await MaterialsViewState.do_query(dbcog, evo_gem)
            gem_override = True

        return mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, gem_override


def mat_use_field(mons, title, max_mons=MAX_MONS_TO_SHOW, qs: Optional[QuerySettings] = None):
    text = None
    if len(mons) == 0:
        text = "None"
    elif len(mons) > max_mons:
        text = f"({len(mons) - max_mons} more monster{'s' if len(mons) - max_mons > 1 else ''}, see `^allmats` for full list)"
    return EmbedField(
        title,
        Box(*(MonsterHeader.box_with_emoji(
            em, qs=qs) for em in mons[:max_mons]), text))


def skillup_field(mons, sec, link, qs):
    text = None
    text2 = None
    if len(mons) == 0:
        text = "None"

    if sec:
        text2 = Box(
            f"({max(len(mons) - MAX_MONS_TO_SHOW, 0) + sec} ",
            LinkedText(f"more monster{'s' if max(len(mons) - MAX_MONS_TO_SHOW, 0) + sec > 1 else ''}", link),
            f", incl. {sec} alt evo{'s' if sec > 1 else ''})",
            delimiter="")
    elif len(mons) > MAX_MONS_TO_SHOW:
        text2 = f"({len(mons) - MAX_MONS_TO_SHOW} more monsters)"

    return EmbedField(
        "Skillups",
        Box(*(MonsterHeader.box_with_emoji(
            em, qs=qs) for em in mons[:MAX_MONS_TO_SHOW]), text, text2))


class MaterialsView(IdBaseView, EvoScrollView):
    VIEW_TYPE = 'Materials'

    @classmethod
    def embed_fields(cls, state: MaterialsViewState) -> List[EmbedField]:
        return [f for f in [
            mat_use_field(state.mats, "Evo materials", qs=state.qs)
            if state.mats or not (state.monster.is_stackable or state.gem_override) else None,
            mat_use_field(state.usedin, "Material for", 10, state.qs)
            if state.usedin else None,
            mat_use_field(state.gemusedin, "Evo gem ({}) is mat for".format(state.gemid),
                          10 if state.gem_override else 5, state.qs)
            if state.gemusedin else None,
            skillup_field(state.skillups, state.skillup_evo_count,
                          state.link, state.qs)
            if not (state.monster.is_stackable or state.gem_override) else None
        ] if f is not None] + [cls.evos_embed_field(state)]
