from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain
from discordmenu.embed.text import LinkedText
from discordmenu.embed.view import EmbedView

from padinfo.common.external_links import puzzledragonx, youtube_search, skyozora, ilmina
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class LinksView:
    VIEW_TYPE = 'Links'

    @staticmethod
    def linksbox(m):
        return Box(
            LinkedText('YouTube', youtube_search(m)),
            LinkedText('Skyozora', skyozora(m)),
            LinkedText('PDX', puzzledragonx(m)),
            LinkedText('Ilmina', ilmina(m)),
            delimiter=' | ')

    @staticmethod
    def embed(m: "MonsterModel", color):
        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                description=LinksView.linksbox(m),
                url=puzzledragonx(m)),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m)))
