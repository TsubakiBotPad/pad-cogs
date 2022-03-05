from typing import TYPE_CHECKING

from discordmenu.embed.components import EmbedAuthor, EmbedMain
from discordmenu.embed.view import EmbedView
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class LookupView:
    VIEW_TYPE = 'Lookup'

    @staticmethod
    def embed(m: "MonsterModel", query_settings: QuerySettings):
        return EmbedView(
            EmbedMain(color=query_settings.color),
            embed_author=EmbedAuthor(
                MonsterHeader.menu_title(m).to_markdown(),
                MonsterLink.header_link(m, query_settings),
                MonsterImage.icon(m.monster_id)))
