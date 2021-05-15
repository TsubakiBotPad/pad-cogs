from discordmenu.embed.control import EmbedControl
from discordmenu.embed.menu import EmbedMenu

from padglobal.view.closable_embed import ClosableEmbedViewState


class ClosableEmbedMenu:
    MENU_TYPE = 'ClosableEmbedMenu'
    message = None

    @staticmethod
    def menu():
        embed = EmbedMenu({}, ClosableEmbedMenu.message_control)
        return embed

    @staticmethod
    def message_control(state: ClosableEmbedViewState):
        view = view_types[state.view_type]
        return EmbedControl(
            [view.embed(state, state.props)],
            []
        )


class ClosableEmbedMenuPanes:
    pass
