from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView

from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

from padinfo.view_state.evos import EvosViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


def _evo_lines(monsters, current_monster):
    if not len(monsters):
        return []
    return [
        MonsterHeader.short_with_emoji(ae, link=ae.monster_id != current_monster.monster_id)
        for ae in sorted(monsters, key=lambda x: int(x.monster_id))
    ]


class EvosView:
    @staticmethod
    def embed(state: EvosViewState):
        fields = [
            EmbedField(
                ("{} evolution" if len(state.alt_versions) == 1 else "{} evolutions").format(len(state.alt_versions)),
                Box(*_evo_lines(state.alt_versions, state.monster)))]

        if state.gem_versions:
            fields.append(
                EmbedField(
                    ("{} evolve gem" if len(state.gem_versions) == 1 else "{} evolve gems").format(len(state.gem_versions)),
                    Box(*_evo_lines(state.gem_versions, state.monster))))

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_v2(state.monster).to_markdown(),
                url=puzzledragonx(state.monster)),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(state.monster)),
            embed_footer=pad_info_footer(),
            embed_fields=fields)
