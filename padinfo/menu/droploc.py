from typing import Optional

from discord import Message
from discordmenu.embed.menu import EmbedMenu
from discordmenu.embed.wrapper import EmbedWrapper
from tsutils.menu.components.panes import MenuPanes

from padinfo.menu.components.evo_scroll_mixin import EvoScrollMenu
from padinfo.view.droploc import DroplocViewState, DroplocView


class DroplocEmoji:
    left = '\N{BLACK LEFT-POINTING TRIANGLE}'
    right = '\N{BLACK RIGHT-POINTING TRIANGLE}'
    home = '\N{HOUSE BUILDING}'
    expand = 'plus'
    contract = 'minus'


class DroplocMenu(EvoScrollMenu):

    @staticmethod
    def get_panes_type():
        return DroplocMenuPanes

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = DroplocMenu.pane_control
        embed = EmbedMenu(DroplocMenuPanes.transitions(), initial_control)
        return embed

    @staticmethod
    async def respond_with_expand(_message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']
        DroplocViewState.expand(ims)
        view_state = await DroplocViewState.deserialize(dbcog, user_config, ims)
        control = DroplocMenu.pane_control(view_state)
        return control

    @staticmethod
    async def respond_with_contract(_message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']
        DroplocViewState.contract(ims)
        view_state = await DroplocViewState.deserialize(dbcog, user_config, ims)
        control = DroplocMenu.pane_control(view_state)
        return control

    @staticmethod
    def pane_control(state: DroplocViewState):
        if state is None:
            return None
        return EmbedWrapper(
            DroplocView.embed(state),
            state.reaction_list or DroplocMenuPanes.emoji_names()
        )


class DroplocMenuPanes(MenuPanes):
    DATA = {
        DroplocEmoji.left: (DroplocMenu.respond_with_left, None),
        DroplocEmoji.right: (DroplocMenu.respond_with_right, None),
        DroplocEmoji.expand: (DroplocMenu.respond_with_expand, None),
        DroplocEmoji.contract: (DroplocMenu.respond_with_contract, None),
    }

    HIDDEN_EMOJIS = [
        DroplocEmoji.home,
    ]
