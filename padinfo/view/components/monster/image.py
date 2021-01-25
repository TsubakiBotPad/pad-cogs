from typing import TYPE_CHECKING

from discordmenu.embed.components import EmbedThumbnail

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

MEDIA_PATH = 'https://d1kpnpud0qoyxf.cloudfront.net/media/'
ICON_TEMPLATE = MEDIA_PATH + 'icons/{0:05d}.png'
RPAD_PIC_TEMPLATE = MEDIA_PATH + 'portraits/{0:05d}.png?cachebuster=2'
VIDEO_TEMPLATE = MEDIA_PATH + 'animated_portraits/{0:05d}.mp4'
GIF_TEMPLATE = MEDIA_PATH + 'animated_portraits/{0:05d}.gif'
ORB_SKIN_TEMPLATE = MEDIA_PATH + 'orb_skins/jp/{0:03d}.png'
ORB_SKIN_CB_TEMPLATE = MEDIA_PATH + 'orb_skins/jp/{0:03d}cb.png'


class MonsterImage:
    @staticmethod
    def icon(m: "MonsterModel"):
        return ICON_TEMPLATE.format(m.monster_id)

    @staticmethod
    def picture(m: "MonsterModel"):
        return RPAD_PIC_TEMPLATE.format(m.monster_id)

    @staticmethod
    def video(m: "MonsterModel"):
        return VIDEO_TEMPLATE.format(m.monster_no_jp)

    @staticmethod
    def gif(m: "MonsterModel"):
        return GIF_TEMPLATE.format(m.monster_no_jp)

    @staticmethod
    def orb_skin(m: "MonsterModel"):
        return ORB_SKIN_TEMPLATE.format(m.orb_skin_id)

    @staticmethod
    def orb_skin_colorblind(m: "MonsterModel"):
        return ORB_SKIN_CB_TEMPLATE.format(m.orb_skin_id)


def monster_thumbnail(m: "MonsterModel"):
    return EmbedThumbnail(MonsterImage.icon(m))
