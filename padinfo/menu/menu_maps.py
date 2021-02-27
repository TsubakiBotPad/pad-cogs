from padinfo.menu.closable_embed import ClosableEmbedMenu, ClosableEmbedMenuPanes
from padinfo.menu.id import IdMenu, IdMenuPanes
from padinfo.menu.leader_skill import LeaderSkillMenu, LeaderSkillMenuPanes
from padinfo.menu.leader_skill_single import LeaderSkillSingleMenu, LeaderSkillSingleMenuPanes
from padinfo.menu.monster_list import MonsterListMenu, MonsterListMenuPanes
from padinfo.menu.series_scroll import SeriesScrollMenu, SeriesScrollMenuPanes
from padinfo.menu.simple_text import SimpleTextMenu, SimpleTextMenuPanes
from padinfo.menu.transforminfo import TransformInfoMenu, TransformInfoMenuPanes

menu_to_panes_map = {
    ClosableEmbedMenu.MENU_TYPE: ClosableEmbedMenuPanes,
    IdMenu.MENU_TYPE: IdMenuPanes,
    LeaderSkillMenu.MENU_TYPE: LeaderSkillMenuPanes,
    LeaderSkillSingleMenu.MENU_TYPE: LeaderSkillSingleMenuPanes,
    MonsterListMenu.MENU_TYPE: MonsterListMenuPanes,
    SeriesScrollMenu.MENU_TYPE: SeriesScrollMenuPanes,
    SimpleTextMenu.MENU_TYPE: SimpleTextMenuPanes,
    TransformInfoMenu.MENU_TYPE: TransformInfoMenuPanes,
}

menu_map = {
    ClosableEmbedMenu.MENU_TYPE: ClosableEmbedMenu,
    IdMenu.MENU_TYPE: IdMenu,
    LeaderSkillMenu.MENU_TYPE: LeaderSkillMenu,
    LeaderSkillSingleMenu.MENU_TYPE: LeaderSkillSingleMenu,
    MonsterListMenu.MENU_TYPE: MonsterListMenu,
    SeriesScrollMenu.MENU_TYPE: SeriesScrollMenu,
    SimpleTextMenu.MENU_TYPE: SimpleTextMenu,
    TransformInfoMenu.MENU_TYPE: TransformInfoMenu,
}