from tsutils.menu.closable_embed_base import ClosableEmbedMenuBase
from padle.view.closable_stats_view import ClosableStatsView


class ClosableStatsMenu(ClosableEmbedMenuBase):
    MENU_TYPE = ClosableStatsView.VIEW_TYPE
    view_types = {
        ClosableStatsView.VIEW_TYPE: ClosableStatsView
    }
