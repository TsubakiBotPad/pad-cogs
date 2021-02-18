from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedThumbnail
from discordmenu.embed.view import EmbedView

from padinfo.common.config import UserConfig
from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.components.view_state_base_id import ViewStateBaseId
from padinfo.view.common import get_monster_from_ims

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class PantheonViewState(ViewStateBaseId):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 pantheon_list: List["MonsterModel"], series_name: str,
                 use_evo_scroll: bool = True,
                 reaction_list: List[str] = None,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, query, color, monster,
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

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')

        return cls(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                   pantheon_list, series_name,
                   use_evo_scroll=use_evo_scroll,
                   reaction_list=reaction_list,
                   extra_state=ims)

    @staticmethod
    async def query(dgcog, monster):
        db_context = dgcog.database
        full_pantheon = db_context.get_monsters_by_series(monster.series_id)
        if not full_pantheon:
            return None, None
        pantheon_list = list(filter(lambda x: db_context.graph.monster_is_base(x), full_pantheon))
        if len(pantheon_list) == 0 or len(pantheon_list) > 20:
            return None, None

        series_name = monster.series.name_en

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
        )]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_v2(state.monster).to_markdown(),
                url=puzzledragonx(state.monster)),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields,
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(state.monster)),
        )
