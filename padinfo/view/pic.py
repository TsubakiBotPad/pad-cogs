from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedBodyImage, EmbedField, EmbedMain
from discordmenu.embed.text import LinkedText, Text
from discordmenu.embed.view import EmbedView
from tsutils.formatting import filesize
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.base import BaseIdView
from padinfo.view.components.evo_scroll_mixin import EvoScrollView
from padinfo.view.components.view_state_base_id import ViewStateBaseId

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


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
    def animation_field(cls, m: "MonsterModel"):
        if not m.has_animation:
            return None
        return EmbedField(
            'Animation',
            Box(
                Box(
                    LinkedText(f'MP4 ({filesize(m.mp4_size)})', MonsterImage.video(m.monster_no_jp)),
                    Text('|'),
                    LinkedText(f'GIF ({filesize(m.gif_size)})', MonsterImage.gif(m.monster_no_jp)),
                    Text('|'),
                    LinkedText(f'GIF ({filesize(m.hq_gif_size)})', MonsterImage.hq_gif(m.monster_no_jp)),
                    delimiter=' '
                )
            ),
        )

    @staticmethod
    def orb_skin_field(m: "MonsterModel"):
        if m.orb_skin_id is None:
            return None
        return EmbedField(
            'Orb Skin',
            Box(
                LinkedText('Regular', MonsterImage.orb_skin(m.orb_skin_id)),
                Text('|'),
                LinkedText('Color Blind', MonsterImage.orb_skin_colorblind(m.orb_skin_id)),
                delimiter=' '
            )
        )

    @classmethod
    def embed(cls, state: PicViewState):
        m = state.monster
        url = MonsterImage.picture(state.monster.monster_id)
        fields = [
            cls.animation_field(m),
            cls.orb_skin_field(m),
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
            embed_footer=embed_footer_with_state(state, qs=state.query_settings),
            embed_fields=fields,
            embed_body_image=EmbedBodyImage(url),
        )
