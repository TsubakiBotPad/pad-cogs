from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedThumbnail
from discordmenu.embed.view import EmbedView

from padinfo.common.config import UserConfig
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
MATS_TYPES = [0, 12, 14, 15]
NO_ATT = 6


class PantheonViewState(ViewStateBaseId):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel", alt_monsters,
                 pantheon_list: List["MonsterModel"], series_name: str,
                 use_evo_scroll: bool = True,
                 reaction_list: List[str] = None,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, query, color, monster, alt_monsters,
                         use_evo_scroll=use_evo_scroll,
                         reaction_list=reaction_list,
                         extra_state=extra_state)
        self.series_name = series_name
        self.pantheon_list = pantheon_list

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
        pantheon_list, series_name = await PantheonViewState.query(dgcog, monster)

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
                   pantheon_list, series_name,
                   use_evo_scroll=use_evo_scroll,
                   reaction_list=reaction_list,
                   extra_state=ims)

    @classmethod
    async def query(cls, dgcog, monster):
        db_context = dgcog.database
        series_name = monster.series.name_en
        full_pantheon = db_context.get_monsters_by_series(monster.series_id)
        if not full_pantheon:
            return None, None

        base_list = list(filter(lambda x: db_context.graph.monster_is_base(x), full_pantheon))
        if len(base_list) > 0 and len(base_list) < MAX_MONS_TO_SHOW:
            return base_list, series_name

        # exclude mats if monster is a mat, otherwise show only mats
        # TODO: filter mats by type
        typed_list = []
        if any(t.value in MATS_TYPES for t in monster.types):
            typed_list = list(filter(lambda x: any(t.value in MATS_TYPES for t in x.types), 
                                     base_list))
        else:
            typed_list = list(filter(lambda x: all(t.value not in MATS_TYPES for t in x.types),
                                     base_list))
        if len(typed_list) > 0 and len(typed_list) < MAX_MONS_TO_SHOW:
            return typed_list, series_name

        base_mon = db_context.graph.get_base_monster(monster)

        rarity_list = list(filter(lambda x: x.rarity == base_mon.rarity, typed_list))
        if len(rarity_list) > 0 and len(rarity_list) < MAX_MONS_TO_SHOW:
            return rarity_list, series_name

        main_att = base_mon.attr1.value
        sub_att = base_mon.attr2.value

        main_att_list = []
        if main_att == NO_ATT:
            main_att_list = list(filter(lambda x: x.attr1.value == sub_att
                                                  or (x.attr1.value == NO_ATT
                                                      and x.attr2.value == sub_att),
                                        rarity_list))
        else:
            main_att_list = list(filter(lambda x: x.attr1.value == main_att, rarity_list))
        if len(main_att_list) > 0 and len(main_att_list) < MAX_MONS_TO_SHOW:
            return main_att_list, series_name

        sub_att_list = list(filter(lambda x: x.attr2.value == sub_att, main_att_list))
        if len(sub_att_list) > 0 and len(sub_att_list) < MAX_MONS_TO_SHOW:
            return sub_att_list, series_name

        # if we've managed to get here, just cut it off
        pantheon_list = sub_att_list[:MAX_MONS_TO_SHOW]

        return pantheon_list, series_name


class PantheonView:
    VIEW_TYPE = 'Pantheon'

    @staticmethod
    def embed(state: PantheonViewState):
        fields = [EmbedField(
            'Pantheon: {}'.format(state.series_name),
            Box(
                *[MonsterHeader.short_with_emoji(m)
                  for m in sorted(state.pantheon_list, key=lambda x: x.monster_no_na)]
            )
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
