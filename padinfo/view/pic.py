from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedBodyImage
from discordmenu.embed.text import LinkedText, Text
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.external_links import puzzledragonx
from padinfo.view.base import BaseIdView
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.components.view_state_base_id import ViewStateBaseId
from padinfo.view.id import evos_embed_field


class PicViewState(ViewStateBaseId):

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': PicView.VIEW_TYPE,
        })
        return ret


class PicView(BaseIdView):
    VIEW_TYPE = 'Pic'

    @classmethod
    def embed(cls, state: PicViewState):
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
        ),
            evos_embed_field(state)
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_maybe_tsubaki(state.monster,
                                                       state.alt_monsters[0].monster.monster_id == cls.TSUBAKI
                                                       ).to_markdown(),
                url=puzzledragonx(state.monster)),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields,
            embed_body_image=EmbedBodyImage(url),
        )
