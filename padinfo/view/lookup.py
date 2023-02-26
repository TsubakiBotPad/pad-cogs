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
    def embed(m: "MonsterModel", qs: QuerySettings):
        return EmbedView(
            EmbedMain(color=qs.embedcolor),
            embed_author=EmbedAuthor(
                MonsterHeader.menu_title(m).to_markdown(),
                MonsterLink.header_link(m, qs),
                MonsterImage.icon(m.monster_id)))
