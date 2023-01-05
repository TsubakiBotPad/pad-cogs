from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedBodyImage, EmbedField, EmbedMain
from discordmenu.embed.text import LinkedText, Text
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.base import BaseIdView
from padinfo.view.components.evo_scroll_mixin import EvoScrollView
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
                    LinkedText('Animation', MonsterImage.spine(state.monster.monster_no_jp)),
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
                color=state.query_settings.embedcolor,
                title=MonsterHeader.menu_title(state.monster,
                                               is_tsubaki=state.alt_monsters[0].monster.monster_id == cls.TSUBAKI,
                                               is_jp_buffed=state.is_jp_buffed).to_markdown(),
                url=MonsterLink.header_link(state.monster, state.query_settings)
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields,
            embed_body_image=EmbedBodyImage(url),
        )
