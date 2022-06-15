from tsutils.menu.closable_embed_base import ClosableEmbedMenuPanes

from padle.menu.closable_embed import ClosableEmbedMenu
from padle.menu.padle_scroll import PADleScrollMenu, PADleMenuPanes
from padle.menu.globalstats import GlobalStatsMenu, GlobalStatsMenuPanes

padle_menu_map = {
    ClosableEmbedMenu.MENU_TYPE: (ClosableEmbedMenu, ClosableEmbedMenuPanes),
    PADleScrollMenu.MENU_TYPE: (PADleScrollMenu, PADleMenuPanes),
    GlobalStatsMenu.MENU_TYPE: (GlobalStatsMenu, GlobalStatsMenuPanes)
}
