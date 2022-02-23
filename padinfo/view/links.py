from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain
from discordmenu.embed.text import LinkedText
from discordmenu.embed.view import EmbedView
from tsutils.tsubaki import MonsterImage, MonsterLink

from padinfo.view.components.monster.header import MonsterHeader

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
    def embed(m: "MonsterModel", color):
        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                description=LinksView.linksbox(m),
                url=MonsterLink.puzzledragonx(m)),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m.monster_id)))
