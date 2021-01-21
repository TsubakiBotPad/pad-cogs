from typing import TYPE_CHECKING

import tsutils

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

INFO_PDX_TEMPLATE = 'http://www.puzzledragonx.com/en/monster.asp?n={}'

MEDIA_PATH = 'https://d1kpnpud0qoyxf.cloudfront.net/media/'
RPAD_PIC_TEMPLATE = MEDIA_PATH + 'portraits/{0:05d}.png?cachebuster=2'
VIDEO_TEMPLATE = MEDIA_PATH + 'animated_portraits/{0:05d}.mp4'
GIF_TEMPLATE = MEDIA_PATH + 'animated_portraits/{0:05d}.gif'
ORB_SKIN_TEMPLATE = MEDIA_PATH + 'orb_skins/jp/{0:03d}.png'
ORB_SKIN_CB_TEMPLATE = MEDIA_PATH + 'orb_skins/jp/{0:03d}cb.png'


def monster_url(m: "MonsterModel"):
    return INFO_PDX_TEMPLATE.format(tsutils.get_pdx_id(m))


def get_pic_url(m: "MonsterModel"):
    return RPAD_PIC_TEMPLATE.format(m.monster_id)


def monster_video_url(m: "MonsterModel"):
    return VIDEO_TEMPLATE.format(m.monster_no_jp)


def monster_gif_url(m: "MonsterModel"):
    return GIF_TEMPLATE.format(m.monster_no_jp)


def monster_orb_skin_url(m: "MonsterModel"):
    return ORB_SKIN_TEMPLATE.format(m.orb_skin_id)


def monster_orb_skin_cb_url(m: "MonsterModel"):
    return ORB_SKIN_CB_TEMPLATE.format(m.orb_skin_id)
