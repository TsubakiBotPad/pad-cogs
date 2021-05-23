from typing import Optional

from discord import Message
from discordmenu.embed.control import EmbedControl
from discordmenu.embed.menu import EmbedMenu
from tsutils.menu.panes import emoji_buttons, MenuPanes

from padinfo.view.awakening_list import AwakeningListViewState, AwakeningListView


class AwakeningListEmoji:
    delete = '\N{CROSS MARK}'
    refresh = '\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}'
    home = emoji_buttons['home']
    prev_page = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
    next_page = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'
    alphabetical = '\N{INPUT SYMBOL FOR LATIN LETTERS}'
    numerical = '\N{INPUT SYMBOL FOR NUMBERS}'


class AwakeningListMenu:
    MENU_TYPE = 'AwakeningList'

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = AwakeningListMenu.awakening_list_control
        embed = EmbedMenu(AwakeningListMenuPanes.transitions(), initial_control)
        return embed

    @staticmethod
    async def respond_with_delete(message: Message, ims, **data):
        return await message.delete()

    @staticmethod
    async def respond_with_left(message: Optional[Message], ims, **data):
        cur_page = ims['page']
        if cur_page == 0:
            ims['page'] = ims['total_pages'] - 1
        else:
            ims['page'] = cur_page - 1
        return await AwakeningListMenu.respond_with_awakening_list(message, ims, **data)

    @staticmethod
    async def respond_with_right(message: Optional[Message], ims, **data):
        cur_page = ims['page']
        if cur_page == ims['total_pages'] - 1:
            ims['page'] = 0
        else:
            ims['page'] = cur_page + 1
        return await AwakeningListMenu.respond_with_awakening_list(message, ims, **data)

    @staticmethod
    async def respond_with_alphabetical(message: Optional[Message], ims, **data):
        ims['sort_type'] = 'alphabetical'
        return await AwakeningListMenu.respond_with_awakening_list(message, ims, **data)

    @staticmethod
    async def respond_with_numerical(message: Optional[Message], ims, **data):
        ims['sort_type'] = 'numerical'
        return await AwakeningListMenu.respond_with_awakening_list(message, ims, **data)

    @staticmethod
    async def respond_with_awakening_list(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        view_state = await AwakeningListViewState.deserialize(dgcog, user_config, ims)
        control = AwakeningListMenu.awakening_list_control(view_state)
        return control

    @staticmethod
    def awakening_list_control(state: AwakeningListViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [AwakeningListView.embed(state)],
            reaction_list
        )


class AwakeningListMenuPanes(MenuPanes):
    INITIAL_EMOJI = AwakeningListEmoji.home

    DATA = {
        AwakeningListEmoji.delete: (AwakeningListMenu.respond_with_delete, None),
        AwakeningListEmoji.home: (AwakeningListMenu.respond_with_awakening_list, AwakeningListView.VIEW_TYPE),
        AwakeningListEmoji.prev_page: (AwakeningListMenu.respond_with_left, AwakeningListView.VIEW_TYPE),
        AwakeningListEmoji.next_page: (AwakeningListMenu.respond_with_right, AwakeningListView.VIEW_TYPE),
        AwakeningListEmoji.alphabetical: (AwakeningListMenu.respond_with_alphabetical, AwakeningListView.VIEW_TYPE),
        AwakeningListEmoji.numerical: (AwakeningListMenu.respond_with_numerical, AwakeningListView.VIEW_TYPE),
    }

    HIDDEN_EMOJIS = [
        AwakeningListEmoji.home,
        AwakeningListEmoji.refresh,
    ]
