from typing import TYPE_CHECKING

from discordmenu.embed.components import EmbedThumbnail

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

MEDIA_PATH = 'https://d1kpnpud0qoyxf.cloudfront.net/media/'
RPAD_PORTRAIT_TEMPLATE = MEDIA_PATH + 'icons/{0:05d}.png'


class MonsterImage:
    @staticmethod
    def icon(m: "MonsterModel"):
        return RPAD_PORTRAIT_TEMPLATE.format(m.monster_id)


def monster_thumbnail(m: "MonsterModel"):
    return EmbedThumbnail(MonsterImage.icon(m))
