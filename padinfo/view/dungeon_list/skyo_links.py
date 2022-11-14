from padinfo.view.dungeon_list.dungeon_list import DungeonListBase, DungeonListViewProps


class SkyoLinksViewProps(DungeonListViewProps):
    ...


class SkyoLinksView(DungeonListBase):
    VIEW_TYPE = 'SkyoLinks'
    dungeon_link = 'https://skyo.tsubakibot.com/{}'
    subdungeon_link = 'https://skyo.tsubakibot.com/{}'
    bad_chars = ['[', ']']
