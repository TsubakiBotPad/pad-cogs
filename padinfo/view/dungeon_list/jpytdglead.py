from typing import TYPE_CHECKING

from discordmenu.embed.text import LinkedText
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.dungeon_list.dungeon_list import DungeonListBase, DungeonListViewProps

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class JpYtDgLeadProps(DungeonListViewProps):
    def __init__(self, dungeons, monster: "MonsterModel"):
        super().__init__(dungeons)
        self.monster = monster


class JpYtDgLeadView(DungeonListBase):
    VIEW_TYPE = 'JpYtDgLead'
    dungeon_link = 'https://www.youtube.com/results?search_query={}%20{}'
    subdungeon_link = 'https://www.youtube.com/results?search_query={}%20{}'
    bad_chars = ['-']
    whitespace = [' ', '　']

    @classmethod
    def format_dg_link(cls, dungeon, props: JpYtDgLeadProps):
        link = cls.dungeon_link.format(dungeon['name'], cls.escape_name(props.monster.name_ja))
        return LinkedText(cls.escape_name(dungeon['name_en']),
                          cls.escape_whitespace(link))

    @classmethod
    def format_sd_link(cls, subdungeon, props: JpYtDgLeadProps):
        return cls.escape_whitespace((
            cls.subdungeon_link.format(subdungeon['name'], cls.escape_name(props.monster.name_ja))))

    @classmethod
    def print_name(cls, subdungeon, props: JpYtDgLeadProps):
        return LinkedText(cls.escape_name(subdungeon['name_en']),
                          cls.format_sd_link(subdungeon, props))

    @classmethod
    def description(cls, props: JpYtDgLeadProps):
        return MonsterHeader.text_with_emoji(props.monster)

    @classmethod
    def escape_whitespace(cls, link):
        for item in cls.whitespace:
            link = link.replace(item, '%20')
        return link
