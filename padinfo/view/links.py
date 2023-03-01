from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedThumbnail
from discordmenu.embed.text import LinkedText
from discordmenu.embed.view import EmbedView
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class LinksView:
    VIEW_TYPE = 'Links'

    @staticmethod
    def linksbox(m):
        return Box(
            LinkedText('YouTube', MonsterLink.youtube_search(m)),
            LinkedText('Skyozora', MonsterLink.skyozora(m)),
            LinkedText('PADIndex', MonsterLink.padindex(m)),
            LinkedText('Ilmina', MonsterLink.ilmina(m)),
            delimiter=' | ')

    @staticmethod
    def embed(m: "MonsterModel", qs: QuerySettings):
        return EmbedView(
            EmbedMain(
                color=qs.embedcolor,
                title=MonsterHeader.menu_title(m).to_markdown(),
                description=LinksView.linksbox(m),
                url=MonsterLink.header_link(m, qs)),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m.monster_id, cachebreak=m.icon_cachebreak)))
