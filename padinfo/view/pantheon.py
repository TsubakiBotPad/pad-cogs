from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedThumbnail
from discordmenu.embed.view import EmbedView

from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view_state.pantheon import PantheonViewState


class PantheonView:
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
