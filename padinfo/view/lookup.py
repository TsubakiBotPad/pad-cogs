from typing import TYPE_CHECKING

from discordmenu.embed.components import EmbedMain, EmbedAuthor
from discordmenu.embed.view import EmbedView
from tsutils.tsubaki import MonsterImage, MonsterLink

from padinfo.view.components.monster.header import MonsterHeader

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
                # TODO: add query_settings
                MonsterLink.header_link(m),
                MonsterImage.icon(m.monster_id)))
