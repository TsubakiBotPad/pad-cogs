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
    bad_chars = []

    @classmethod
    def format_dg_link(cls, dungeon, props: JpYtDgLeadProps):
        return LinkedText(cls.escape_name(dungeon['name']),
                          cls.dungeon_link.format(dungeon['idx'], props.monster.name_ja))

    @classmethod
    def format_sd_link(cls, subdungeon, props: JpYtDgLeadProps):
        return cls.subdungeon_link.format(subdungeon['idx'], props.monster.name_ja)

    @classmethod
    def description(cls, props: JpYtDgLeadProps):
        return MonsterHeader.text_with_emoji(props.monster)
