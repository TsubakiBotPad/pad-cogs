from typing import List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.text import LinkedText
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.closable_embed import ClosableEmbedViewState


class DungeonListViewProps:
    def __init__(self, dungeons: List[dict]):
        self.dungeons = dungeons


class DungeonListBase:
    VIEW_TYPE: str
    dungeon_link: str
    subdungeon_link: str
    bad_chars: list

    @classmethod
    def embed_fields(cls, dungeons, props):
        ret = []
        for dungeon in dungeons:
            ret.append(cls.format_dg_link(dungeon, props))
            for subdungeon in dungeon['subdungeons']:
                ret.append(Box(
                    "\u200b \u200b \u200b \u200b \u200b ",
                    cls.print_name(subdungeon, props),
                    delimiter=''
                ))
        return [EmbedField('Dungeons', Box(*ret, delimiter='\n'))]

    @classmethod
    def format_dg_link(cls, dungeon, _props: DungeonListViewProps):
        return LinkedText(cls.escape_name(dungeon['name_en']),
                          cls.dungeon_link.format(dungeon['idx']))

    @classmethod
    def print_name(cls, subdungeon, props: DungeonListViewProps):
        return LinkedText(cls.escape_name(subdungeon['name_en']),
                          cls.format_sd_link(subdungeon, props))

    @classmethod
    def format_sd_link(cls, subdungeon, _props: DungeonListViewProps):
        return cls.subdungeon_link.format(subdungeon['idx'])

    @classmethod
    def escape_name(cls, name):
        for char in cls.bad_chars:
            name = name.replace(char, '')
        return name

    @classmethod
    def description(cls, _props: DungeonListViewProps):
        return 'The following dungeons were found.'

    @classmethod
    def embed(cls, state: ClosableEmbedViewState, props: DungeonListViewProps):
        return EmbedView(
            EmbedMain(
                color=state.query_settings.embedcolor,
                description=cls.description(props)
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=cls.embed_fields(props.dungeons, props)
        )
