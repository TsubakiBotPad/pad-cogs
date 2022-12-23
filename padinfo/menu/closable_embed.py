from tsutils.menu.closable_embed_base import ClosableEmbedMenuBase

from padinfo.view.awakening_help import AwakeningHelpView
from padinfo.view.dungeon_list.jp_dungeon_name import JpDungeonNameView
from padinfo.view.dungeon_list.jpytdglead import JpYtDgLeadView
from padinfo.view.dungeon_list.jptwtdglead import JpTwtDgLeadView
from padinfo.view.dungeon_list.skyo_links import SkyoLinksView
from padinfo.view.experience_curve import ExperienceCurveView
from padinfo.view.id_traceback import IdTracebackView


class ClosableEmbedMenu(ClosableEmbedMenuBase):
    view_types = {
        AwakeningHelpView.VIEW_TYPE: AwakeningHelpView,
        IdTracebackView.VIEW_TYPE: IdTracebackView,
        ExperienceCurveView.VIEW_TYPE: ExperienceCurveView,
        SkyoLinksView.VIEW_TYPE: SkyoLinksView,
        JpDungeonNameView.VIEW_TYPE: JpDungeonNameView,
        JpYtDgLeadView.VIEW_TYPE: JpYtDgLeadView,
        JpTwtDgLeadView.VIEW_TYPE: JpTwtDgLeadView,
    }
