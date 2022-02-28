from typing import TYPE_CHECKING

from discordmenu.embed.components import EmbedMain, EmbedAuthor
from discordmenu.embed.view import EmbedView
from tsutils.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterImage, MonsterLink

from padinfo.view.components.monster.header import MonsterHeader

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class LookupView:
    VIEW_TYPE = 'Lookup'

    @staticmethod
    def embed(m: "MonsterModel", color, query_settings: QuerySettings):
        return EmbedView(
            EmbedMain(color=color),
            embed_author=EmbedAuthor(
                MonsterHeader.long_v2(m).to_markdown(),
                MonsterLink.header_link(m, query_settings),
                MonsterImage.icon(m.monster_id)))
