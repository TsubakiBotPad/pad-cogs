from discordmenu.embed.control import EmbedControl
from discordmenu.embed.menu import EmbedMenu

from padinfo.menu.common import MenuPanes
from padinfo.view.closable_embed import ClosableEmbedViewState
from padinfo.view.id_traceback import IdTracebackView

emoji_button_names = ['\N{CROSS MARK}']

view_types = {
    IdTracebackView.VIEW_TYPE: IdTracebackView
}


class ClosableEmbedMenu:
    MENU_TYPE = 'ClosableEmbedMenu'
    EMOJI_BUTTON_NAMES = emoji_button_names
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
            ClosableEmbedMenu.EMOJI_BUTTON_NAMES
        )


class ClosableEmbedMenuPanes(MenuPanes):
    pass
