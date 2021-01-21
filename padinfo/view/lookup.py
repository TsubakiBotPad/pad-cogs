from typing import TYPE_CHECKING

from discordmenu.embed.components import EmbedMain
from discordmenu.embed.menu import EmbedView

from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.monster.header import MonsterHeader

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class LookupView:
    @staticmethod
    def embed(m: "MonsterModel", color):
        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=puzzledragonx(m)))
