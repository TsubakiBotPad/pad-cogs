from typing import TYPE_CHECKING, List, Optional

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedBodyImage, EmbedField, EmbedThumbnail
from discordmenu.embed.text import LinkedText, Text
from tsutils.formatting import filesize
from tsutils.tsubaki.links import MonsterImage

from padinfo.view.components.evo_scroll_mixin import EvoScrollView
from padinfo.view.components.view_state_base_id import ViewStateBaseId, IdBaseView

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class PicViewState(ViewStateBaseId):

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': PicView.VIEW_TYPE,
        })
        return ret


class PicView(IdBaseView, EvoScrollView):
    VIEW_TYPE = 'Pic'

    @classmethod
    def animation_field(cls, m: "MonsterModel"):
        if not m.has_animation:
            return None
        return EmbedField(
            'Animation',
            Box(
                Box(
                    LinkedText(f'MP4 ({filesize(m.mp4_size)})', MonsterImage.video(m.monster_id)),
                    Text('|'),
                    LinkedText(f'GIF ({filesize(m.gif_size)})', MonsterImage.gif(m.monster_id)),
                    Text('|'),
                    LinkedText(f'GIF ({filesize(m.hq_gif_size)})', MonsterImage.hq_gif(m.monster_id)),
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
    def embed_fields(cls, state: PicViewState) -> List[EmbedField]:
        m = state.monster
        return [
            cls.animation_field(m),
            cls.orb_skin_field(m),
            cls.evos_embed_field(state)
        ]

    @classmethod
    def embed_body_image(cls, state: PicViewState) -> Optional[EmbedBodyImage]:
        return EmbedBodyImage(MonsterImage.picture(state.monster.monster_id))

    @classmethod
    def embed_thumbnail(cls, state: PicViewState) -> Optional[EmbedThumbnail]:
        return None
