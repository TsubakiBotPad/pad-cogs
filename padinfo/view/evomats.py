from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.menu import EmbedView

from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


def mat_use_field(usedin, title):
    if len(usedin) > 5:
        return EmbedField(
            title,
            Box(f"{len(usedin)} monsters"),
            inline=True)
    elif len(usedin) == 0:
        return EmbedField(
            title,
            Box("None"),
            inline=True)
    else:
        return EmbedField(
            title,
            Box(*(MonsterHeader.short(em, True) for em in usedin)),
            inline=True)


class EvoMatsView:
    @staticmethod
    def embed(m: "MonsterModel", mats, usedin, gemusedin, color):
        fields = [mat_use_field(mats, "Evo Materials")]
        if usedin:
            fields.append(mat_use_field(usedin, "Material For"))
        if gemusedin:
            fields.append(mat_use_field(gemusedin, "Evo Gem is Mat For"))

        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=puzzledragonx(m)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m)),
            embed_footer=pad_info_footer(),
            embed_fields=fields
        )
