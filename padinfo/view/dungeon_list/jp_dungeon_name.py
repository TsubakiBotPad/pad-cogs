from padinfo.view.dungeon_list.dungeon_list import DungeonListBase, DungeonListViewProps


class JpDungeonNameViewProps(DungeonListViewProps):
    ...


class JpDungeonNameView(DungeonListBase):
    VIEW_TYPE = 'JpDungeonName'
    dungeon_link = ''
    subdungeon_link = ''
    bad_chars = ['']

    @classmethod
    def format_dg_link(cls, dungeon, props):
        return cls.escape_name(dungeon['name'])

    @classmethod
    def print_name(cls, subdungeon, props: DungeonListViewProps):
        return cls.escape_name(subdungeon['name'])
