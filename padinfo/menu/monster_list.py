from typing import Optional

from discord import Message
from discordmenu.embed.menu import EmbedMenu
from tsutils import char_to_emoji

from padinfo.menu.common import emoji_buttons, MenuPanes
from padinfo.menu.id import IdMenu, IdMenuPanes, IdMenuEmoji
from padinfo.view.id import IdView
from padinfo.view.monster_list import MonsterListViewState


class MonsterListEmoji:
    home = emoji_buttons['home']
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
    refresh = '\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}'
    reset = emoji_buttons['reset']


class MonsterListMenu:
    MENU_TYPE = 'MonsterListMenu'
    CHILD_MENU_TYPE = 'IdMenu'

    @staticmethod
    def menu():
        embed = EmbedMenu(MonsterListMenuPanes.transitions())
        return embed

    @staticmethod
    async def respond_with_refresh(message: Optional[Message], ims, **data):
        # this is only called once on message load
        if data.get('child_message_id'):
            ims['child_message_id'] = data['child_message_id']
        return await MonsterListMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_reset(message: Optional[Message], ims, **data):
        # replace with the overview list after the child menu changes
        return await MonsterListMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_monster_list(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        view_state = await MonsterListViewState.deserialize(dgcog, user_config, ims)
        if view_state is None:
            return None
        return view_state.control()

    @staticmethod
    async def respond_with_n(message: Optional[Message], ims, _n, **data):
        return await MonsterListMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_0(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 0, **data)

    @staticmethod
    async def respond_with_1(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 1, **data)

    @staticmethod
    async def respond_with_2(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 2, **data)

    @staticmethod
    async def respond_with_3(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 3, **data)

    @staticmethod
    async def respond_with_4(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 4, **data)

    @staticmethod
    async def respond_with_5(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 5, **data)

    @staticmethod
    async def respond_with_6(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 6, **data)

    @staticmethod
    async def respond_with_7(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 7, **data)

    @staticmethod
    async def respond_with_8(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 8, **data)

    @staticmethod
    async def respond_with_9(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 9, **data)

    @staticmethod
    async def respond_with_10(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 10, **data)

    @staticmethod
    def click_child_number(ims, emoji_clicked, **_data):
        emoji_response = IdMenuEmoji.refresh \
            if MonsterListMenuPanes.respond_to_emoji_with_child(emoji_clicked) else None
        if emoji_response is None:
            return None, {}
        n = MonsterListMenuPanes.emoji_names().index(emoji_clicked)
        extra_ims = {
            'is_child': True,
            'resolved_monster_id': int(ims['monster_list'][n]),
            'reaction_list': IdMenuPanes.emoji_names(),
            'menu_type': IdMenu.MENU_TYPE,
        }
        return emoji_response, extra_ims


class MonsterListMenuPanes(MenuPanes):
    INITIAL_EMOJI = MonsterListEmoji.home
    DATA = {
        # tuple parts: parent_response, pane_type, respond_with_child
        MonsterListEmoji.home: (MonsterListMenu.respond_with_monster_list, MonsterListEmoji.home, None),
        MonsterListEmoji.zero: (
            MonsterListMenu.respond_with_0, IdView.VIEW_TYPE, MonsterListMenu.click_child_number),
        MonsterListEmoji.one: (
            MonsterListMenu.respond_with_1, IdView.VIEW_TYPE, MonsterListMenu.click_child_number),
        MonsterListEmoji.two: (
            MonsterListMenu.respond_with_2, IdView.VIEW_TYPE, MonsterListMenu.click_child_number),
        MonsterListEmoji.three: (
            MonsterListMenu.respond_with_3, IdView.VIEW_TYPE, MonsterListMenu.click_child_number),
        MonsterListEmoji.four: (
            MonsterListMenu.respond_with_4, IdView.VIEW_TYPE, MonsterListMenu.click_child_number),
        MonsterListEmoji.five: (
            MonsterListMenu.respond_with_5, IdView.VIEW_TYPE, MonsterListMenu.click_child_number),
        MonsterListEmoji.six: (
            MonsterListMenu.respond_with_6, IdView.VIEW_TYPE, MonsterListMenu.click_child_number),
        MonsterListEmoji.seven: (
            MonsterListMenu.respond_with_7, IdView.VIEW_TYPE, MonsterListMenu.click_child_number),
        MonsterListEmoji.eight: (
            MonsterListMenu.respond_with_8, IdView.VIEW_TYPE, MonsterListMenu.click_child_number),
        MonsterListEmoji.nine: (
            MonsterListMenu.respond_with_9, IdView.VIEW_TYPE, MonsterListMenu.click_child_number),
        MonsterListEmoji.ten: (
            MonsterListMenu.respond_with_10, IdView.VIEW_TYPE, MonsterListMenu.click_child_number),
        MonsterListEmoji.refresh: (
            MonsterListMenu.respond_with_refresh, None, None),
        MonsterListEmoji.reset: (
            MonsterListMenu.respond_with_reset, None, None)
    }
    HIDDEN_EMOJIS = [
        MonsterListEmoji.home,
        MonsterListEmoji.refresh,
        MonsterListEmoji.reset,
    ]

    @classmethod
    def get_initial_reaction_list(cls, number_of_evos: int):
        return cls.emoji_names()[:number_of_evos]
