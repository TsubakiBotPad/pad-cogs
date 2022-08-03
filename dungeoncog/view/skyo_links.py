from typing import List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.text import LinkedText
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.closable_embed import ClosableEmbedViewState


class SkyoLinksViewProps:
    def __init__(self, dungeons: List[dict], link=True):
        self.dungeons = dungeons
        self.link = link


class SkyoLinksView:
    VIEW_TYPE = 'SkyoLinks'
    dungeon_link = 'https://skyo.tsubakibot.com/{}'
    subdungeon_link = 'https://skyo.tsubakibot.com/{}'
    bad_chars = ['[', ']']

    @classmethod
    def embed_fields(cls, dungeons, link):
        ret = []
        for dungeon in dungeons:
            if link:
                ret.append(LinkedText(cls.escape_name(dungeon['name']), cls.dungeon_link.format(dungeon['idx'])))
            else:
                ret.append(cls.escape_name(dungeon['name']))
            for subdungeon in dungeon['subdungeons']:
                if link:
                    ret.append(Box(
                        "\u200b \u200b \u200b \u200b \u200b ",
                        LinkedText(cls.escape_name(subdungeon['name']), cls.subdungeon_link.format(subdungeon['idx'])),
                        delimiter=''
                    ))
                else:
                    ret.append("\u200b \u200b \u200b \u200b \u200b " + cls.escape_name(subdungeon['name']))
        return [EmbedField('Dungeons', Box(*ret, delimiter='\n'))]

    @classmethod
    def escape_name(cls, name):
        for char in cls.bad_chars:
            name = name.replace(char, '')
        return name

    @classmethod
    def embed(cls, state: ClosableEmbedViewState, props: SkyoLinksViewProps):
        return EmbedView(
            EmbedMain(
                color=state.query_settings.embedcolor,
                description='The following dungeons were found.'
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=cls.embed_fields(props.dungeons, props.link)
        )
