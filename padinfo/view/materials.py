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

MAX_SKILLUPS_TO_SHOW = 5
MAX_MATFOR_TO_SHOW = 5

def mat_use_field(usedin, title, overflow=None):
    if not usedin:
        return EmbedField(
            title,
            Box("None"))
    elif len(usedin) > MAX_MATFOR_TO_SHOW and overflow is None:
        return EmbedField(
            title,
            Box(f"{len(usedin)} monsters"))
    elif overflow and len(usedin) > overflow:
        return EmbedField(
            title,
            Box(
                *(MonsterHeader.short_with_emoji(em) for em in usedin[:overflow]),
                f"({len(usedin) - overflow} more {title.lower()})"))
    else:
        return EmbedField(
            title,
            Box(*(MonsterHeader.short_with_emoji(em) for em in usedin)))


class MaterialView:
    @staticmethod
    def embed(m: "MonsterModel", mats, usedin, gemusedin, skillups, color):
        fields = [mat_use_field(mats, "Evo materials")]
        if usedin:
            fields.append(mat_use_field(usedin, "Material for"))
        if gemusedin:
            fields.append(mat_use_field(gemusedin, "Evo gem is mat for"))
        fields.append(mat_use_field(skillups, "Skillups", MAX_SKILLUPS_TO_SHOW))

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
