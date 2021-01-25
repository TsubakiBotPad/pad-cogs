from discordmenu.embed.components import EmbedFooter, EmbedMain

from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import monster_thumbnail


async def make_base_embed_v2(m: "MonsterModel", embed_color):
    main = EmbedMain(
        color=embed_color,
        title=MonsterHeader.long_v2(m)
    )
    footer = EmbedFooter('Requester may click the reactions below to switch tabs')
    thumbnail = monster_thumbnail(m)
    return main, footer, thumbnail


def pad_info_footer():
    return EmbedFooter('Requester may click the reactions below to switch tabs')
