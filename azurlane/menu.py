import string
from functools import partial
from typing import Optional

from discord import Message
from discordmenu.embed.menu import EmbedMenu
from discordmenu.embed.wrapper import EmbedWrapper
from tsutils.emoji import char_to_emoji
from tsutils.menu.components.panes import MenuPanes

from azurlane.azurlane_view import AzurlaneView, AzurlaneViewState

alid_emoji_order = [char_to_emoji(x) for x in [*range(11), *string.ascii_uppercase]]


class AzurlaneMenu:
    MENU_TYPE = AzurlaneView.VIEW_TYPE

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = AzurlaneMenu.pane_control
        embed = EmbedMenu(AzurlaneMenuPanes.transitions(), initial_control)
        return embed

    @staticmethod
    async def respond_with_n(n, message: Optional[Message], ims, **data):
        ims['current_index'] = n
        return await AzurlaneMenu.respond_with_pane(message, ims, **data)

    @classmethod
    async def respond_with_pane(cls, message: Optional[Message], ims, **data):
        alcog = data['alcog']
        user_config = data['user_config']
        view_state = await AzurlaneViewState.deserialize(alcog, user_config, ims)
        return AzurlaneMenu.pane_control(view_state)

    @classmethod
    def pane_control(cls, state: AzurlaneViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedWrapper(
            AzurlaneView.embed(state),
            reaction_list
        )


class AzurlaneMenuPanes(MenuPanes):
    NON_MONSTER_EMOJI_COUNT = 0

    DATA = {emoji: (partial(AzurlaneMenu.respond_with_n, c), AzurlaneView.VIEW_TYPE)
            for c, emoji in enumerate(alid_emoji_order)}

    @classmethod
    def get_initial_reaction_list(cls, number_of_skins: int):
        return cls.emoji_names()[:number_of_skins + cls.NON_MONSTER_EMOJI_COUNT]
