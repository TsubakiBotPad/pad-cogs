from tsutils.menu.closable_embed_base import ClosableEmbedMenuPanes
from tsutils.menu.simple_text import SimpleTextMenu, SimpleTextMenuPanes

from padinfo.menu.awakening_list import AwakeningListMenu, AwakeningListMenuPanes
from padinfo.menu.button_info import ButtonInfoMenu, ButtonInfoMenuPanes
from padinfo.menu.closable_embed import ClosableEmbedMenu
from padinfo.menu.favcard import FavcardMenu, FavcardMenuPanes
from padinfo.menu.id import IdMenu, IdMenuPanes
from padinfo.menu.leader_skill import LeaderSkillMenu, LeaderSkillMenuPanes
from padinfo.menu.leader_skill_single import LeaderSkillSingleMenu, LeaderSkillSingleMenuPanes
from padinfo.menu.monster_list import MonsterListMenu, MonsterListMenuPanes
from padinfo.menu.na_diff import NaDiffMenu, NaDiffMenuPanes
from padinfo.menu.scroll import ScrollMenuPanes
from padinfo.menu.series_scroll import SeriesScrollMenu, SeriesScrollMenuPanes
from padinfo.menu.transforminfo import TransformInfoMenu, TransformInfoMenuPanes
from padinfo.view.favcard import FavcardViewState
from padinfo.view.monster_list.all_mats import AllMatsViewState
from padinfo.view.monster_list.id_search import IdSearchViewState
from padinfo.view.monster_list.scroll import ScrollViewState
from padinfo.view.monster_list.static_monster_list import StaticMonsterListViewState

padinfo_menu_map = {
    AwakeningListMenu.MENU_TYPE: (AwakeningListMenu, AwakeningListMenuPanes),
    ButtonInfoMenu.MENU_TYPE: (ButtonInfoMenu, ButtonInfoMenuPanes),
    ClosableEmbedMenu.MENU_TYPE: (ClosableEmbedMenu, ClosableEmbedMenuPanes),
    IdMenu.MENU_TYPE: (IdMenu, IdMenuPanes),
    LeaderSkillMenu.MENU_TYPE: (LeaderSkillMenu, LeaderSkillMenuPanes),
    LeaderSkillSingleMenu.MENU_TYPE: (LeaderSkillSingleMenu, LeaderSkillSingleMenuPanes),
    MonsterListMenu.MENU_TYPE: (MonsterListMenu, MonsterListMenuPanes),
    AllMatsViewState.VIEW_STATE_TYPE: (MonsterListMenu, MonsterListMenuPanes),
    IdSearchViewState.VIEW_STATE_TYPE: (MonsterListMenu, MonsterListMenuPanes),
    ScrollViewState.VIEW_STATE_TYPE: (MonsterListMenu, ScrollMenuPanes),
    StaticMonsterListViewState.VIEW_STATE_TYPE: (MonsterListMenu, MonsterListMenuPanes),
    SeriesScrollMenu.MENU_TYPE: (SeriesScrollMenu, SeriesScrollMenuPanes),
    SimpleTextMenu.MENU_TYPE: (SimpleTextMenu, SimpleTextMenuPanes),
    TransformInfoMenu.MENU_TYPE: (TransformInfoMenu, TransformInfoMenuPanes),
    NaDiffMenu.MENU_TYPE: (NaDiffMenu, NaDiffMenuPanes),
    FavcardViewState.VIEW_STATE_TYPE: (FavcardMenu, FavcardMenuPanes),
}
