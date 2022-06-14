from tsutils.menu.closable_embed_base import ClosableEmbedMenuBase
from padle.view.confirmation import PADleMonsterConfirmationView


class ClosableEmbedMenu(ClosableEmbedMenuBase):
    MENU_TYPE = PADleMonsterConfirmationView.VIEW_TYPE
    view_types = {
        PADleMonsterConfirmationView.VIEW_TYPE: PADleMonsterConfirmationView
    }
