from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedThumbnail
from discordmenu.embed.view import EmbedView

from padinfo.common.config import UserConfig
from padinfo.common.emoji_map import get_attribute_emoji_by_monster, get_attribute_emoji_by_enum
from padinfo.common.external_links import puzzledragonx
from padinfo.view.common import get_monster_from_ims
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.components.view_state_base_id import ViewStateBaseId
from padinfo.view.id import evos_embed_field

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

MAX_MONS_TO_SHOW = 20
MAT_TYPES = [0, 12, 14, 15]
NO_ATT = 6


class PantheonViewState(ViewStateBaseId):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel", alt_monsters,
                 pantheon_list: List["MonsterModel"], series_name: str, base_monster,
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

        alt_monsters = cls.get_alt_monsters(dgcog, monster)
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
    async def query(cls, dgcog, monster):
        db_context = dgcog.database
        series_name = monster.series.name_en
        full_pantheon = db_context.get_monsters_by_series(monster.series_id)
        if not full_pantheon:
            return None, None, None

        base_mon = db_context.graph.get_base_monster(monster)

        base_list = [m for m in full_pantheon if db_context.graph.monster_is_base(m)]
        if len(base_list) > 0 and len(base_list) < MAX_MONS_TO_SHOW:
            return base_list, series_name, base_mon

        # if monster has only mat types, show only mats, otherwise show everything else
        type_list = []
        if all(t.value in MAT_TYPES for t in monster.types):
            series_name += ' (Mat)'
            type_list = [m for m in base_list if all(t.value in MAT_TYPES for t in m.types)]
        else:
            type_list = [m for m in base_list if any(t.value not in MAT_TYPES for t in m.types)]
        if len(type_list) > 0 and len(type_list) < MAX_MONS_TO_SHOW:
            return type_list, series_name, base_mon

        filters = ' [Filters: '

        rarity_list = [m for m in type_list if m.rarity == base_mon.rarity]
        filters += '{}*'.format(base_mon.rarity)
        if len(rarity_list) > 0 and len(rarity_list) < MAX_MONS_TO_SHOW:
            return rarity_list, series_name + filters + ']', base_mon

        main_att = base_mon.attr1
        sub_att = base_mon.attr2

        main_att_list = []
        att_emoji = None
        if main_att.value == NO_ATT:
            att_emoji = get_attribute_emoji_by_enum(sub_att)
            main_att_list = [m for m in rarity_list if m.attr1.value == sub_att.value
                                                       or (m.attr1.value == NO_ATT
                                                           and m.attr2.value == sub_att.value)]
        else:
            att_emoji = get_attribute_emoji_by_enum(main_att)
            main_att_list = [m for m in rarity_list if m.attr1.value == main_att.value
                                                       or (m.attr1.value == NO_ATT
                                                           and m.attr2.value == main_att.value)]
        # don't concatenate filter this time, because if we go to subatt we only want one emoji
        if len(main_att_list) > 0 and len(main_att_list) < MAX_MONS_TO_SHOW:
            return main_att_list, series_name + filters + ' {}]'.format(att_emoji), base_mon

        sub_att_list = [m for m in main_att_list if m.attr1.value == main_att.value
                                                    and m.attr2.value == sub_att.value]
        filters += ' {}'.format(get_attribute_emoji_by_monster(base_mon))
        if len(sub_att_list) > 0 and len(sub_att_list) < MAX_MONS_TO_SHOW:
            return sub_att_list, series_name + filters + ']', base_mon

        # if we've managed to get here, just cut it off
        pantheon_list = sub_att_list[:MAX_MONS_TO_SHOW]

        return pantheon_list, series_name + filters + '] (still too many, truncated)', base_mon


class PantheonView:
    VIEW_TYPE = 'Pantheon'

    @staticmethod
    def _pantheon_lines(monsters, base_monster):
        if not len(monsters):
            return []
        return [
            MonsterHeader.short_with_emoji(mon, link=mon.monster_id != base_monster.monster_id)
            for mon in sorted(monsters, key=lambda x: int(x.monster_id))
        ]

    @staticmethod
    def embed(state: PantheonViewState):
        fields = [EmbedField(
            'Pantheon: {}'.format(state.series_name),
            Box(*PantheonView._pantheon_lines(state.pantheon_list, state.base_monster))
        ),
            evos_embed_field(state)]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_v2(state.monster).to_markdown(),
                url=puzzledragonx(state.monster)),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields,
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(state.monster)),
        )
