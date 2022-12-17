from typing import Dict, List, Optional, TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedField, EmbedMain, EmbedThumbnail
from discordmenu.embed.text import BoldText, LabeledText, Text
from discordmenu.embed.view import EmbedView
from tsutils.enums import Server
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.query_settings.enums import CardLevelModifier, CardModeModifier, CardPlusModifier
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.custom_emoji import get_awakening_emoji, get_emoji
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.common import get_monster_from_ims, invalid_monster_text
from padinfo.view.components.base_id_main_view import BaseIdMainView
from padinfo.view.components.evo_scroll_mixin import EvoScrollView, MonsterEvolution
from padinfo.view.components.view_state_base_id import ViewStateBaseId

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.models.awakening_model import AwakeningModel
    from dbcog.models.awoken_skill_model import AwokenSkillModel
    from dbcog.database_context import DbContext


class IdQueriedProps:
    def __init__(self, acquire_raw, base_rarity, transform_base, true_evo_type_raw, previous_evolutions,
                 previous_transforms, awoken_skill_map: Dict[int, "AwokenSkillModel"]):
        self.previous_evolutions = previous_evolutions
        self.true_evo_type_raw = true_evo_type_raw
        self.transform_base = transform_base
        self.previous_transforms = previous_transforms
        self.base_rarity = base_rarity
        self.acquire_raw = acquire_raw
        self.awoken_skill_map = awoken_skill_map


class IdViewState(ViewStateBaseId):
    nadiff_na_only_text = ', which is only in NA'
    nadiff_jp_only_text = ', which is only in JP'
    nadiff_identical_text = ', which is the same in NA & JP'

    def __init__(self, original_author_id, menu_type, raw_query, query, monster: "MonsterModel",
                 alt_monsters: List[MonsterEvolution], is_jp_buffed: bool, query_settings: QuerySettings,
                 id_queried_props: IdQueriedProps,
                 fallback_message: str = None, reaction_list: List[str] = None,
                 is_child: bool = False, extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, query, monster,
                         alt_monsters, is_jp_buffed, query_settings,
                         reaction_list=reaction_list,
                         extra_state=extra_state)
        self.fallback_message = fallback_message
        self.is_child = is_child
        self.acquire_raw = id_queried_props.acquire_raw
        self.base_rarity = id_queried_props.base_rarity
        self.previous_evolutions = id_queried_props.previous_evolutions
        self.previous_transforms = id_queried_props.previous_transforms
        self.transform_base: "MonsterModel" = id_queried_props.transform_base
        self.true_evo_type_raw = id_queried_props.true_evo_type_raw
        self.awoken_skill_map = id_queried_props.awoken_skill_map

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': IdView.VIEW_TYPE,
            'is_child': self.is_child,
            'message': self.fallback_message,
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        # for numberscroll getting to a gap in monster book, or 1, or last monster
        if ims.get('unsupported_transition'):
            return None
        monster = await get_monster_from_ims(dbcog, ims)
        alt_monsters = cls.get_alt_monsters_and_evos(dbcog, monster)
        id_queried_props = await IdViewState.do_query(dbcog, monster)

        raw_query = ims['raw_query']
        # This is to support the 2 vs 1 monster query difference between ^ls and ^id
        query = ims.get('query') or raw_query
        query_settings = QuerySettings.deserialize(ims.get('query_settings'))
        menu_type = ims['menu_type']
        original_author_id = ims['original_author_id']
        reaction_list = ims.get('reaction_list')
        fallback_message = ims.get('message')
        is_child = ims.get('is_child')
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)

        return cls(original_author_id, menu_type, raw_query, query, monster,
                   alt_monsters, is_jp_buffed, query_settings,
                   id_queried_props,
                   fallback_message=fallback_message,
                   reaction_list=reaction_list,
                   is_child=is_child,
                   extra_state=ims)

    async def set_server(self, dbcog, server: Server):
        self.query_settings.server = server
        self.monster = dbcog.database.graph.get_monster(self.monster.monster_id, server=server)
        self.alt_monsters = self.get_alt_monsters_and_evos(dbcog, self.monster)
        id_queried_props = await self.do_query(dbcog, self.monster)
        self.transform_base = id_queried_props.transform_base
        self.true_evo_type_raw = id_queried_props.true_evo_type_raw
        self.acquire_raw = id_queried_props.acquire_raw
        self.base_rarity = id_queried_props.base_rarity

    @classmethod
    async def do_query(cls, dbcog, monster) -> IdQueriedProps:
        db_context = dbcog.database
        id_queried_props = await IdViewState._get_monster_misc_info(db_context, monster)
        return id_queried_props

    @classmethod
    async def _get_monster_misc_info(cls, db_context: "DbContext", monster) -> IdQueriedProps:
        transform_base = db_context.graph.get_transform_base(monster)
        true_evo_type_raw = db_context.graph.true_evo_type(monster).value
        acquire_raw = db_context.graph.monster_acquisition(monster)
        base_rarity = db_context.graph.get_base_monster(monster).rarity
        previous_evolutions = db_context.graph.get_all_prev_evolutions(monster, include_self=True)
        previous_transforms = db_context.graph.get_all_prev_transforms(monster, include_self=False)
        awoken_skill_map = db_context.awoken_skill_map
        return IdQueriedProps(acquire_raw, base_rarity, transform_base, true_evo_type_raw, previous_evolutions,
                              previous_transforms, awoken_skill_map)

    def set_na_diff_invalid_message(self, ims: dict) -> bool:
        message = self.get_na_diff_invalid_message()
        if message is not None:
            ims['message'] = message
            return True
        return False

    def get_na_diff_invalid_message(self) -> Optional[str]:
        monster: "MonsterModel" = self.monster
        if monster.on_na and not monster.on_jp:
            return invalid_monster_text(self.query, monster, self.nadiff_na_only_text)
        if monster.on_jp and not monster.on_na:
            return invalid_monster_text(self.query, monster, self.nadiff_jp_only_text)
        if not self.is_jp_buffed:
            return invalid_monster_text(self.query, monster, self.nadiff_identical_text)
        return None


def _get_awakening_text(awakening: "AwakeningModel"):
    return get_awakening_emoji(awakening.awoken_skill_id, awakening.name)


def _get_awakening_emoji_for_stats(m: "MonsterModel", i: int):
    return get_awakening_emoji(i) if m.awakening_count(i) and not m.is_equip else ''


def _get_stat_text(stat, lb_stat, icon):
    return Box(
        Text(str(stat)),
        Text("({})".format(lb_stat)) if lb_stat else None,
        Text(icon) if icon else None,
        delimiter=' '
    )


def _monster_is_enhance(m: "MonsterModel"):
    return any(x if x.name == 'Enhance' else None for x in m.types)


class IdView(BaseIdMainView, EvoScrollView):
    VIEW_TYPE = 'Id'

    @classmethod
    def all_awakenings_row(cls, m: "MonsterModel", transform_base):
        if len(m.awakenings) == 0:
            return Box(Text('No Awakenings'))

        return Box(
            Box(
                get_emoji(cls.up_emoji_name) if m != transform_base else '',
                cls.normal_awakenings_row(m),
                delimiter=' '
            ),
            Box(
                '\N{DOWN-POINTING RED TRIANGLE}',
                IdView.all_awakenings_row(transform_base, transform_base),
                delimiter=' '
            ) if m != transform_base else None,
            cls.super_awakenings_row(m),
        )

    @staticmethod
    def misc_info(m: "MonsterModel", true_evo_type_raw: str, acquire_raw: str, base_rarity: str):
        rarity = Box(
            LabeledText('Rarity', str(m.rarity)),
            Text('({})'.format(LabeledText('Base', str(base_rarity)).to_markdown())),
            Text("" if m.orb_skin_id is None else "(Orb Skin)"),
            Text("" if m.bgm_id is None else "(BGM)"),
            delimiter=' '
        )

        cost = LabeledText('Cost', str(m.cost))
        acquire = BoldText(acquire_raw) if acquire_raw else None
        series = BoldText(m.series.name_en) if m.series else None
        valid_true_evo_types = ("Reincarnated", "Assist", "Pixel", "Super Reincarnated")
        true_evo_type = BoldText(true_evo_type_raw) if true_evo_type_raw in valid_true_evo_types else None

        return Box(rarity, cost, series, acquire, true_evo_type)

    @classmethod
    def stats(cls, m: "MonsterModel", previous_evolutions, query_settings: QuerySettings):
        plus = cls.get_plus_status(previous_evolutions, query_settings.cardplus)
        multiplayer = query_settings.cardmode == CardModeModifier.coop
        lb_level = 110 if query_settings.cardlevel == CardLevelModifier.lv110 else 120
        hp, atk, rcv, weighted = m.stats(plus=plus, multiplayer=multiplayer)

        lb_hp, lb_atk, lb_rcv, lb_weighted = (None, None, None, None)
        if m.limit_mult > 0:
            lb_hp, lb_atk, lb_rcv, lb_weighted = m.stats(plus=plus, lv=lb_level, multiplayer=multiplayer)

        return Box(
            LabeledText('HP', _get_stat_text(hp, lb_hp, _get_awakening_emoji_for_stats(m, 1))),
            LabeledText('ATK', _get_stat_text(atk, lb_atk, _get_awakening_emoji_for_stats(m, 2))),
            LabeledText('RCV', _get_stat_text(rcv, lb_rcv, _get_awakening_emoji_for_stats(m, 3))),
            LabeledText('Fodder EXP', "{:,}".format(m.fodder_exp)) if _monster_is_enhance(m) else None
        )

    @staticmethod
    def get_plus_status(previous_evolutions: List["MonsterModel"], cardplus: CardPlusModifier):
        if cardplus == CardPlusModifier.plus0:
            return 0
        if all([m.level == 1 and m.is_material for m in previous_evolutions]):
            return 0
        return 297 if cardplus == CardPlusModifier.plus297 else 0

    @classmethod
    def stats_header(cls, m: "MonsterModel", previous_evolutions, query_settings: QuerySettings):
        voice_emoji = get_awakening_emoji(63) if m.awakening_count(63) and not m.is_equip else ''

        multiboost_emoji = None
        if m.awakening_count(30) and query_settings.cardmode == CardModeModifier.coop:
            multiboost_emoji = get_emoji('misc_multiboost')

        plus_emoji = get_emoji('plus_297')
        if cls.get_plus_status(previous_evolutions, query_settings.cardplus) != 297:
            plus_emoji = get_emoji('plus_0')

        lb_emoji = get_emoji('lv110')
        if m.limit_mult > 0 and query_settings.cardlevel == CardLevelModifier.lv120:
            lb_emoji = get_emoji('lv120')

        header = Box(
            Text(voice_emoji),
            Text(plus_emoji),
            Text(multiboost_emoji) if multiboost_emoji else None,
            Text('Stats'),
            Text('({}, +{}%)'.format(lb_emoji, m.limit_mult)) if m.limit_mult else None,
            delimiter=' '
        )
        return header

    @classmethod
    def embed(cls, state: IdViewState):
        m = state.monster
        qs = state.query_settings
        fields = [
            EmbedField(
                '/'.join(['{}'.format(t.name) for t in m.types]),
                Box(
                    IdView.all_awakenings_row(m, state.transform_base),
                    cls.killers_row(m, state.transform_base)
                )
            ),
            EmbedField(
                'Inheritable' if m.is_inheritable else 'Not inheritable',
                IdView.misc_info(m, state.true_evo_type_raw, state.acquire_raw, state.base_rarity),
                inline=True
            ),
            EmbedField(
                IdView.stats_header(m, state.previous_evolutions, qs).to_markdown(),
                IdView.stats(m, state.previous_evolutions, qs),
                inline=True
            ),
            EmbedField(
                cls.active_skill_header(m, state.previous_transforms).to_markdown(),
                Text(cls.active_skill_text(m.active_skill, state.awoken_skill_map, qs.skilldisplay))
            ),
            EmbedField(
                cls.leader_skill_header(m, qs.lsmultiplier, state.transform_base).to_markdown(),
                cls.leader_skill_text(m.leader_skill, qs.skilldisplay)
            ),
            cls.evos_embed_field(state)
        ]

        return EmbedView(
            EmbedMain(
                color=qs.embedcolor,
                title=MonsterHeader.menu_title(m,
                                               is_tsubaki=state.alt_monsters[0].monster.monster_id == cls.TSUBAKI,
                                               is_jp_buffed=state.is_jp_buffed).to_markdown(),
                url=MonsterLink.header_link(m, qs)),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m.monster_id)),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields)
