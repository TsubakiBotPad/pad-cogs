from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedBodyImage
from discordmenu.embed.view import EmbedView
from discordmenu.embed.text import LinkedText, Text

from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view_state.pic import PicViewState


class PicView:
    @staticmethod
    def embed(state: PicViewState):
        url = MonsterImage.picture(state.monster)
        animated = state.monster.has_animation
        fields = [EmbedField(
            'Extra Links',
            Box(
                Box(
                    Text('Animation:'),
                    LinkedText('(MP4)', MonsterImage.video(state.monster)),
                    Text('|'),
                    LinkedText('(GIF)', MonsterImage.gif(state.monster)),
                    delimiter=' '
                ) if animated else None,
                Box(
                    Text('Orb Skin:'),
                    LinkedText('Regular', MonsterImage.orb_skin(state.monster)),
                    Text('|'),
                    LinkedText('Color Blind', MonsterImage.orb_skin_colorblind(state.monster)),
                    delimiter=' '
                ) if state.monster.orb_skin_id else None,
            )
        )]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_v2(state.monster).to_markdown(),
                url=puzzledragonx(state.monster)),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields,
            embed_body_image=EmbedBodyImage(url),
        )
