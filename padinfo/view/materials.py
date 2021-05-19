from typing import List, TYPE_CHECKING, Optional

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.text import LinkedText
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.config import UserConfig
from padinfo.common.external_links import ilmina_skill
from padinfo.common.external_links import puzzledragonx
from padinfo.view.base import BaseIdView
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.components.view_state_base_id import ViewStateBaseId, MonsterEvolution
from padinfo.view.common import get_monster_from_ims
from padinfo.view.id import evos_embed_field

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

MAX_MONS_TO_SHOW = 5


class MaterialsViewState(ViewStateBaseId):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 alt_monsters: List[MonsterEvolution],
                 mats: List["MonsterModel"], usedin: List["MonsterModel"], gemid: Optional[str],
                 gemusedin: List["MonsterModel"], skillups: List["MonsterModel"], skillup_evo_count: int, link: str,
                 gem_override: bool,
                 use_evo_scroll: bool = True,
                 reaction_list: List[str] = None,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, query, color, monster, alt_monsters,
                         reaction_list=reaction_list,
                         use_evo_scroll=use_evo_scroll,
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
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        monster = await get_monster_from_ims(dgcog, ims)
        mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, stackable = \
            await MaterialsViewState.query(dgcog, monster)

        if mats is None:
            return None

        alt_monsters = cls.get_alt_monsters_and_evos(dgcog, monster)
        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        menu_type = ims['menu_type']
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        reaction_list = ims.get('reaction_list')

        return cls(original_author_id, menu_type, raw_query, query, user_config.color, monster, alt_monsters,
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


def mat_use_field(mons, title, max_mons=MAX_MONS_TO_SHOW):
    text = None
    if len(mons) == 0:
        text = "None"
    elif len(mons) > max_mons:
        text = f"({len(mons) - max_mons} more monster{'s' if len(mons) - max_mons > 1 else ''}, see `^allmats` for full list)"
    return EmbedField(
        title,
        Box(*(MonsterHeader.short_with_emoji(em) for em in mons[:max_mons]), text))


def skillup_field(mons, sec, link):
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
        Box(*(MonsterHeader.short_with_emoji(em) for em in mons[:MAX_MONS_TO_SHOW]), text, text2))


class MaterialsView(BaseIdView):
    VIEW_TYPE = 'Materials'

    @classmethod
    def embed(cls, state: MaterialsViewState):
        # m: "MonsterModel", color, mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link
        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_maybe_tsubaki(state.monster,
                                                       state.alt_monsters[0].monster.monster_id == cls.TSUBAKI
                                                       ).to_markdown(),
                url=puzzledragonx(state.monster)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(state.monster)),
            embed_footer=embed_footer_with_state(state),
            embed_fields=[f for f in [
                mat_use_field(state.mats, "Evo materials")
                if state.mats or not (state.monster.is_stackable or state.gem_override) else None,
                mat_use_field(state.usedin, "Material for", 10)
                if state.usedin else None,
                mat_use_field(state.gemusedin, "Evo gem ({}) is mat for".format(state.gemid),
                              10 if state.gem_override else 5)
                if state.gemusedin else None,
                skillup_field(state.skillups, state.skillup_evo_count, state.link)
                if not (state.monster.is_stackable or state.gem_override) else None
            ] if f is not None] + [evos_embed_field(state)]
        )
