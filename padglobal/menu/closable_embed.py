from tsutils.menu.closable_embed_base import ClosableEmbedMenuBase

from padglobal.view.which import WhichView


class ClosableEmbedMenu(ClosableEmbedMenuBase):
    view_types = {
        WhichView.VIEW_TYPE: WhichView
    }
