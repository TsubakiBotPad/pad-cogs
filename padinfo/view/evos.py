from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView

from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

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
    def embed(m: "MonsterModel", alt_versions, gem_versions, color):
        fields = [
            EmbedField(
                ("{} evolution" if len(alt_versions) == 1 else "{} evolutions").format(len(alt_versions)),
                Box(*_evo_lines(alt_versions, m)))]

        if gem_versions:
            fields.append(
                EmbedField(
                    ("{} evolve gem" if len(gem_versions) == 1 else "{} evolve gems").format(len(gem_versions)),
                    Box(*_evo_lines(gem_versions, m))))

        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=puzzledragonx(m)),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m)),
            embed_footer=pad_info_footer(),
            embed_fields=fields)
