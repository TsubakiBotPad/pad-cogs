from padle.view.personal_stats_view import PersonalStatsView
from tsutils.menu.closable_embed_base import ClosableEmbedMenuBase


class PersonalStatsMenu(ClosableEmbedMenuBase):
    MENU_TYPE = PersonalStatsView.VIEW_TYPE
    view_types = {
        PersonalStatsView.VIEW_TYPE: PersonalStatsView
    }
