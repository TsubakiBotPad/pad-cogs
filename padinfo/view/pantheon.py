from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedThumbnail
from discordmenu.embed.menu import EmbedView

from padinfo.common.external_links import monster_url
from padinfo.view.components.base import pad_info_footer
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class PantheonView:
    @staticmethod
    def embed(m: "MonsterModel", color, pantheon_list, series_name):
        fields = [EmbedField(
            'Pantheon: {}'.format(series_name),
            Box(
                *[MonsterHeader.short_with_emoji(m)
                  for m in sorted(pantheon_list, key=lambda x: x.monster_no_na)]
            )
        )]

        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=monster_url(m)),
            embed_footer=pad_info_footer(),
            embed_fields=fields,
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m)),
        )
