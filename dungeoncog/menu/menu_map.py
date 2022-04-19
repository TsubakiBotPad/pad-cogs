from tsutils.menu.closable_embed_base import ClosableEmbedMenuPanes

from dungeoncog.menu.closable_embed import ClosableEmbedMenu
from dungeoncog.menu.dungeon import DungeonMenu, DungeonMenuPanes
from dungeoncog.menu.simple import SimpleMenu, SimpleMenuPanes

dungeon_menu_map = {
    SimpleMenu.MENU_TYPE: (SimpleMenu, SimpleMenuPanes),
    DungeonMenu.MENU_TYPE: (DungeonMenu, DungeonMenuPanes),
    ClosableEmbedMenu.MENU_TYPE: (ClosableEmbedMenu, ClosableEmbedMenuPanes),
}
