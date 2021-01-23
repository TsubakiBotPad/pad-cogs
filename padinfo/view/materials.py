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


def mat_use_field(mons, title):
    return EmbedField(
        title,
        Box(*((MonsterHeader.short_with_emoji(em) for em in mons)
              if len(mons) <= MAX_MONS_TO_SHOW
              else [f"{len(mons)} monsters"]),
            "None" if not mons else None))

def skillup_field(mons):
    text = None
    if len(mons) == 0:
        text = "None"
    elif len(mons) > MAX_MONS_TO_SHOW:
        text = f"({len(mons) - MAX_MONS_TO_SHOW} more monsters)"

    return EmbedField(
        "Skillups",
        Box(*(MonsterHeader.short_with_emoji(em) for em in mons[:MAX_MONS_TO_SHOW]), text))

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
                skillup_field(skillups)
            ] if f is not None]
        )
