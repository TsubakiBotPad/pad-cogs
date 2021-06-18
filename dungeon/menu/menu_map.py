from dungeon.menu.dungeon import DungeonMenu, DungeonMenuPanes
from dungeon.menu.simple import SimpleMenu, SimpleMenuPanes

dungeon_menu_map = {
    SimpleMenu.MENU_TYPE: (SimpleMenu, SimpleMenuPanes),
    DungeonMenu.MENU_TYPE: (DungeonMenu, DungeonMenuPanes)
}
