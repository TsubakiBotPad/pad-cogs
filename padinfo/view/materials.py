from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.menu import EmbedView
from discordmenu.embed.text import LinkedText

from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

MAX_MONS_TO_SHOW = 5


def mat_use_field(mons, title, max_mons=MAX_MONS_TO_SHOW):
    text = None
    if len(mons) == 0:
        text = "None"
    elif len(mons) > max_mons:
        text = f"({len(mons) - max_mons} more monster{'s' if len(mons) - max_mons > 1 else ''})"
    return EmbedField(
        title,
        Box(*(MonsterHeader.short_with_emoji(em) for em in mons[:max_mons]), text))


def skillup_field(mons, sec, link):
    text = None
    text2 = None
    if len(mons) == 0:
        text = "None"

    if sec:
        text2 = Box(
            f"({max(len(mons) - MAX_MONS_TO_SHOW, 0) + sec} ",
            LinkedText(f"more monster{'s' if max(len(mons) - MAX_MONS_TO_SHOW, 0) + sec > 1 else ''}", link),
            f", incl. {sec} alt evo{'s' if sec > 1 else ''})",
            delimiter="")
    elif len(mons) > MAX_MONS_TO_SHOW:
        text2 = f"({len(mons) - MAX_MONS_TO_SHOW} more monsters)"

    return EmbedField(
        "Skillups",
        Box(*(MonsterHeader.short_with_emoji(em) for em in mons[:MAX_MONS_TO_SHOW]), text, text2))


class MaterialView:
    @staticmethod
    def embed(m: "MonsterModel", color, mats, usedin, gemid, gemusedin, skillups, sec, link):
        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=puzzledragonx(m)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m)),
            embed_footer=pad_info_footer(),
            embed_fields=[f for f in [
                mat_use_field(mats, "Evo materials") if mats or not m.stackable else None,
                mat_use_field(usedin, "Material for", 10) if usedin else None,
                mat_use_field(gemusedin, "Evo gem ({}) is mat for".format(gemid)) if gemusedin else None,
                skillup_field(skillups, sec, link) if not m.stackable else None
            ] if f is not None]
        )
