from tsutils.menu.closable_embed_base import ClosableEmbedMenuBase

from dungeoncog.view.skyo_links import SkyoLinksView


class ClosableEmbedMenu(ClosableEmbedMenuBase):
    view_types = {
        SkyoLinksView.VIEW_TYPE: SkyoLinksView
    }
