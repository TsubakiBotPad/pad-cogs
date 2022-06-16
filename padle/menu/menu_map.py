from padle.menu.closable_embed import ClosableEmbedMenu
from padle.menu.globalstats import GlobalStatsMenu, GlobalStatsMenuPanes
from padle.menu.padle_scroll import PADleScrollMenu, PADleMenuPanes
from padle.menu.personal_stats import PersonalStatsMenu
from tsutils.menu.closable_embed_base import ClosableEmbedMenuPanes

padle_menu_map = {
    ClosableEmbedMenu.MENU_TYPE: (ClosableEmbedMenu, ClosableEmbedMenuPanes),
    PersonalStatsMenu.MENU_TYPE: (PersonalStatsMenu, ClosableEmbedMenuPanes),
    PADleScrollMenu.MENU_TYPE: (PADleScrollMenu, PADleMenuPanes),
    GlobalStatsMenu.MENU_TYPE: (GlobalStatsMenu, GlobalStatsMenuPanes),
}
