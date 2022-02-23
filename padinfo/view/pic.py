from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedBodyImage
from discordmenu.embed.text import LinkedText, Text
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.tsubaki import MonsterImage, MonsterLink

from padinfo.view.base import BaseIdView
from padinfo.view.components.evo_scroll_mixin import EvoScrollView
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.view_state_base_id import ViewStateBaseId


class PicViewState(ViewStateBaseId):

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': PicView.VIEW_TYPE,
        })
        return ret


class PicView(BaseIdView, EvoScrollView):
    VIEW_TYPE = 'Pic'

    @classmethod
    def embed(cls, state: PicViewState):
        url = MonsterImage.picture(state.monster.monster_id)
        animated = state.monster.has_animation
        fields = [EmbedField(
            'Extra Links',
            Box(
                Box(
                    Text('Animation:'),
                    LinkedText('(MP4)', MonsterImage.video(state.monster.monster_no_jp)),
                    Text('|'),
                    LinkedText('(GIF)', MonsterImage.gif(state.monster.monster_no_jp)),
                    delimiter=' '
                ) if animated else None,
                Box(
                    Text('Orb Skin:'),
                    LinkedText('Regular', MonsterImage.orb_skin(state.monster.orb_skin_id)),
                    Text('|'),
                    LinkedText('Color Blind', MonsterImage.orb_skin_colorblind(state.monster.orb_skin_id)),
                    delimiter=' '
                ) if state.monster.orb_skin_id else None,
            )
        ),
            cls.evos_embed_field(state)
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.fmt_id_header(state.monster,
                                                  state.alt_monsters[0].monster.monster_id == cls.TSUBAKI,
                                                  state.is_jp_buffed).to_markdown(),
                url=MonsterLink.puzzledragonx(state.monster)),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields,
            embed_body_image=EmbedBodyImage(url),
        )
