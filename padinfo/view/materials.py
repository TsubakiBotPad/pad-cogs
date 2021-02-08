from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from discordmenu.embed.text import LinkedText

from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer, pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view_state.materials import MaterialsViewState

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


class MaterialsView:
    @staticmethod
    def embed(state: MaterialsViewState):
        # m: "MonsterModel", color, mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link
        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_v2(state.monster).to_markdown(),
                url=puzzledragonx(state.monster)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(state.monster)),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=[f for f in [
                mat_use_field(state.mats, "Evo materials") if state.mats or not state.monster.is_stackable else None,
                mat_use_field(state.usedin, "Material for", 10) if state.usedin else None,
                mat_use_field(state.gemusedin, "Evo gem ({}) is mat for".format(state.gemid)) if state.gemusedin else None,
                skillup_field(state.skillups, state.skillup_evo_count, state.link) if not state.monster.is_stackable else None
            ] if f is not None]
        )
