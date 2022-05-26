from typing import Optional

from discord import Message
from discordmenu.embed.control import EmbedControl
from discordmenu.embed.menu import EmbedMenu
from tsutils.emoji import char_to_emoji
from tsutils.menu.components.panes import MenuPanes

from azurlane.azurlane_view import AzurlaneViewState, AzurlaneView


class AzurlaneEmoji:
    zero = char_to_emoji('0')
    one = char_to_emoji('1')
    two = char_to_emoji('2')
    three = char_to_emoji('3')
    four = char_to_emoji('4')
    five = char_to_emoji('5')
    six = char_to_emoji('6')
    seven = char_to_emoji('7')
    eight = char_to_emoji('8')
    nine = char_to_emoji('9')
    ten = char_to_emoji('10')


class AzurlaneMenu:
    MENU_TYPE = AzurlaneView.VIEW_TYPE

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = AzurlaneMenu.pane_control
        embed = EmbedMenu(AzurlaneMenuPanes.transitions(), initial_control)
        return embed

    @staticmethod
    async def respond_with_n(message: Optional[Message], ims, n, **data):
        ims['current_index'] = n
        return await AzurlaneMenu.respond_with_pane(message, ims, **data)

    @staticmethod
    async def respond_with_0(message: Optional[Message], ims, **data):
        return await AzurlaneMenu.respond_with_n(message, ims, 0, **data)

    @staticmethod
    async def respond_with_1(message: Optional[Message], ims, **data):
        return await AzurlaneMenu.respond_with_n(message, ims, 1, **data)

    @staticmethod
    async def respond_with_2(message: Optional[Message], ims, **data):
        return await AzurlaneMenu.respond_with_n(message, ims, 2, **data)

    @staticmethod
    async def respond_with_3(message: Optional[Message], ims, **data):
        return await AzurlaneMenu.respond_with_n(message, ims, 3, **data)

    @staticmethod
    async def respond_with_4(message: Optional[Message], ims, **data):
        return await AzurlaneMenu.respond_with_n(message, ims, 4, **data)

    @staticmethod
    async def respond_with_5(message: Optional[Message], ims, **data):
        return await AzurlaneMenu.respond_with_n(message, ims, 5, **data)

    @staticmethod
    async def respond_with_6(message: Optional[Message], ims, **data):
        return await AzurlaneMenu.respond_with_n(message, ims, 6, **data)

    @staticmethod
    async def respond_with_7(message: Optional[Message], ims, **data):
        return await AzurlaneMenu.respond_with_n(message, ims, 7, **data)

    @staticmethod
    async def respond_with_8(message: Optional[Message], ims, **data):
        return await AzurlaneMenu.respond_with_n(message, ims, 8, **data)

    @staticmethod
    async def respond_with_9(message: Optional[Message], ims, **data):
        return await AzurlaneMenu.respond_with_n(message, ims, 9, **data)

    @staticmethod
    async def respond_with_10(message: Optional[Message], ims, **data):
        return await AzurlaneMenu.respond_with_n(message, ims, 10, **data)

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
        return EmbedControl(
            [AzurlaneView.embed(state)],
            reaction_list
        )


class AzurlaneMenuPanes(MenuPanes):

    NON_MONSTER_EMOJI_COUNT = 0

    DATA = {
        AzurlaneEmoji.zero: (
            AzurlaneMenu.respond_with_0, AzurlaneView.VIEW_TYPE),
        AzurlaneEmoji.one: (
            AzurlaneMenu.respond_with_1, AzurlaneView.VIEW_TYPE),
        AzurlaneEmoji.two: (
            AzurlaneMenu.respond_with_2, AzurlaneView.VIEW_TYPE),
        AzurlaneEmoji.three: (
            AzurlaneMenu.respond_with_3, AzurlaneView.VIEW_TYPE),
        AzurlaneEmoji.four: (
            AzurlaneMenu.respond_with_4, AzurlaneView.VIEW_TYPE),
        AzurlaneEmoji.five: (
            AzurlaneMenu.respond_with_5, AzurlaneView.VIEW_TYPE),
        AzurlaneEmoji.six: (
            AzurlaneMenu.respond_with_6, AzurlaneView.VIEW_TYPE),
        AzurlaneEmoji.seven: (
            AzurlaneMenu.respond_with_7, AzurlaneView.VIEW_TYPE),
        AzurlaneEmoji.eight: (
            AzurlaneMenu.respond_with_8, AzurlaneView.VIEW_TYPE),
        AzurlaneEmoji.nine: (
            AzurlaneMenu.respond_with_9, AzurlaneView.VIEW_TYPE),
        AzurlaneEmoji.ten: (
            AzurlaneMenu.respond_with_10, AzurlaneView.VIEW_TYPE),
    }

    @classmethod
    def get_initial_reaction_list(cls, number_of_skins: int):
        return cls.emoji_names()[:number_of_skins + cls.NON_MONSTER_EMOJI_COUNT]
