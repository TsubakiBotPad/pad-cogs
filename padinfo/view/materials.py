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

MAX_MONS_TO_SHOW = 5


def mat_use_field(usedin, title, overflow=0):
    if len(usedin) > MAX_MONS_TO_SHOW:
        return EmbedField(
            title,
            Box(
                *(MonsterHeader.short_with_emoji(em) for em in usedin[:overflow]),
                f"({len(usedin) - overflow} more {title.lower()})" if overflow else f"{len(usedin)} monsters"))
    return EmbedField(
        title,
        Box(*(MonsterHeader.short_with_emoji(em) for em in usedin),
            "None" if not usedin else None))


class MaterialView:
    @staticmethod
    def embed(m: "MonsterModel", mats, usedin, gemusedin, skillups, color):
        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=puzzledragonx(m)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m)),
            embed_footer=pad_info_footer(),
            embed_fields=[f for f in [
                mat_use_field(mats, "Evo materials"),
                mat_use_field(usedin, "Material for") if usedin else None,
                mat_use_field(gemusedin, "Evo gem is mat for") if gemusedin else None,
                mat_use_field(skillups, "Skillups", MAX_MONS_TO_SHOW)
            ] if f is not None]
        )
