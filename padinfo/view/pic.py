from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedBodyImage
from discordmenu.embed.menu import EmbedView
from discordmenu.embed.text import LinkedText, Text

from padinfo.common.external_links import monster_url, monster_video_url, monster_gif_url, monster_orb_skin_url, \
    monster_orb_skin_cb_url, get_pic_url
from padinfo.view.components.base import pad_info_footer
from padinfo.view.components.monster.header import MonsterHeader

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class PicsView:
    @staticmethod
    def embed(m: "MonsterModel", color):
        url = get_pic_url(m)
        animated = m.has_animation
        fields = [EmbedField(
            'Extra Links',
            Box(
                Box(
                    Text('Animation:'),
                    LinkedText('(MP4)', monster_video_url(m)),
                    Text('|'),
                    LinkedText('(GIF)', monster_gif_url(m)),
                    delimiter=' '
                ) if animated else None,
                Box(
                    Text('Orb Skin:'),
                    LinkedText('Regular', monster_orb_skin_url(m)),
                    Text('|'),
                    LinkedText('Color Blind', monster_orb_skin_cb_url(m)),
                    delimiter=' '
                ) if m.orb_skin_id else None,
            )
        )]

        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=monster_url(m)),
            embed_footer=pad_info_footer(),
            embed_fields=fields,
            embed_body_image=EmbedBodyImage(url),
        )
