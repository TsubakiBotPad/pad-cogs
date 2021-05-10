from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedThumbnail
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.config import UserConfig
from padinfo.common.emoji_map import get_attribute_emoji_by_monster, get_attribute_emoji_by_enum, \
    get_rarity_emoji
from padinfo.common.external_links import puzzledragonx
from padinfo.view.base import BaseIdView
from padinfo.view.common import get_monster_from_ims
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.components.view_state_base_id import ViewStateBaseId, MonsterEvolution
from padinfo.view.id import evos_embed_field

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

MAX_MONS_TO_SHOW = 20
MAT_TYPES = ['Evolve', 'Awoken', 'Enhance', 'Vendor']
NIL_ATT = 'Nil'


class PantheonViewState(ViewStateBaseId):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel", alt_monsters,
                 pantheon_list: List[MonsterEvolution], series_name: str, base_monster,
                 use_evo_scroll: bool = True,
                 reaction_list: List[str] = None,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, query, color, monster, alt_monsters,
                         use_evo_scroll=use_evo_scroll,
                         reaction_list=reaction_list,
                         extra_state=extra_state)
        self.series_name = series_name
        self.pantheon_list = pantheon_list
        self.base_monster = base_monster

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': PantheonView.VIEW_TYPE,
        })
        return ret

    @classmethod
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        monster = await get_monster_from_ims(dgcog, ims)
        pantheon_list, series_name, base_monster = await PantheonViewState.query(dgcog, monster)

        if pantheon_list is None:
            return None

        alt_monsters = cls.get_alt_monsters_and_evos(dgcog, monster)
        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')

        return cls(original_author_id, menu_type, raw_query, query, user_config.color, monster, alt_monsters,
                   pantheon_list, series_name, base_monster,
                   use_evo_scroll=use_evo_scroll,
                   reaction_list=reaction_list,
                   extra_state=ims)

    @classmethod
    def make_series_name(cls, series_name, filter_strings):
        return '{} [Filters: {}]'.format(series_name, ' '.join(filter_strings))

    @classmethod
    async def query(cls, dgcog, monster):
        # filtering rules:
        # 1. don't show monsters that only have mat types (or show only mats if monster is a mat)
        # 2. if still too many, show only monsters with the same base rarity
        # 3. if still too many, show only monsters with the same base main attribute (any monster
        #        with nil main attribute is compared using its subattribute)
        # 4. if still too many, show only monsters that match both base attributes
        # 5. if still too many, truncate (and probably redefine pantheon)

        db_context = dgcog.database
        series_name = monster.series.name_en
        full_pantheon = db_context.get_monsters_by_series(monster.series_id)
        if not full_pantheon:
            return None, None, None

        base_mon = db_context.graph.get_base_monster(monster)

        base_list = [m for m in full_pantheon if db_context.graph.monster_is_base(m)]
        if 0 < len(base_list) <= MAX_MONS_TO_SHOW:
            return base_list, series_name, base_mon

        # if monster has only mat types, show only mats, otherwise show everything else
        type_list = []
        if all(t.name in MAT_TYPES for t in monster.types):
            series_name += ' (Mat)'
            type_list = [m for m in base_list if all(t.name in MAT_TYPES for t in m.types)]
        else:
            type_list = [m for m in base_list if any(t.name not in MAT_TYPES for t in m.types)]
        if 0 < len(type_list) <= MAX_MONS_TO_SHOW:
            return type_list, series_name, base_mon

        filters = []

        rarity_list = [m for m in type_list if m.rarity == base_mon.rarity]
        filters.append(get_rarity_emoji(base_mon.rarity))
        if 0 < len(rarity_list) <= MAX_MONS_TO_SHOW:
            return rarity_list, cls.make_series_name(series_name, filters), base_mon

        main_att = base_mon.attr1
        sub_att = base_mon.attr2

        # if the monster has nil main attribute, do comparisons using its subattribute
        # if any monster in the list has nil main attribute, also compare using its subattribute
        main_att_list = []
        att_emoji = None
        if main_att.name == NIL_ATT:
            att_emoji = get_attribute_emoji_by_enum(sub_att)
            main_att_list = [m for m in rarity_list if m.attr1.name == sub_att.name
                             or (m.attr1.name == NIL_ATT
                                 and m.attr2.name == sub_att.name)]
        else:
            att_emoji = get_attribute_emoji_by_enum(main_att)
            main_att_list = [m for m in rarity_list if m.attr1.name == main_att.name
                             or (m.attr1.name == NIL_ATT
                                 and m.attr2.name == main_att.name)]
        if 0 < len(main_att_list) <= MAX_MONS_TO_SHOW:
            # append after check this time, because if we go to subatt we only want one emoji
            filters.append(att_emoji)
            return main_att_list, cls.make_series_name(series_name, filters), base_mon

        sub_att_list = [m for m in main_att_list if m.attr1.name == main_att.name
                        and m.attr2.name == sub_att.name]
        filters.append(get_attribute_emoji_by_monster(base_mon))
        if 0 < len(sub_att_list) <= MAX_MONS_TO_SHOW:
            return sub_att_list, cls.make_series_name(series_name, filters), base_mon

        # if we've managed to get here, just cut it off
        pantheon_list = sub_att_list[:MAX_MONS_TO_SHOW]
        filters.append('(still too many, truncated)')

        return pantheon_list, cls.make_series_name(series_name, filters), base_mon


def _pantheon_lines(monsters, base_monster):
    if not len(monsters):
        return []
    return [
        MonsterHeader.short_with_emoji(mon, link=mon.monster_id != base_monster.monster_id)
        for mon in sorted(monsters, key=lambda x: int(x.monster_id))
    ]


class PantheonView(BaseIdView):
    VIEW_TYPE = 'Pantheon'

    @classmethod
    def embed(cls, state: PantheonViewState):
        fields = [EmbedField(
            'Pantheon: {}'.format(state.series_name),
            Box(*_pantheon_lines(state.pantheon_list, state.base_monster))
        ),
            evos_embed_field(state)]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_maybe_tsubaki(state.monster,
                                                       state.alt_monsters[0].monster.monster_id == cls.TSUBAKI
                                                       ).to_markdown(),
                url=puzzledragonx(state.monster)),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields,
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(state.monster)),
        )
