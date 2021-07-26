from typing import TYPE_CHECKING

from discordmenu.embed.components import EmbedMain, EmbedAuthor
from discordmenu.embed.view import EmbedView

from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class LookupView:
    VIEW_TYPE = 'Lookup'

    @staticmethod
    def embed(m: "MonsterModel", color):
        return EmbedView(
            EmbedMain(color=color),
            embed_author=EmbedAuthor(
                MonsterHeader.long_v2(m).to_markdown(),
                puzzledragonx(m),
                MonsterImage.icon(m)))
