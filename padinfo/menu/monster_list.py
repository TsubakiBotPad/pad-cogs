from typing import Optional

from discord import Message
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from tsutils import char_to_emoji

from padinfo.menu.common import emoji_buttons, MenuPanes
from padinfo.menu.id import IdMenu, IdMenuPanes, IdMenuPaneNames
from padinfo.view.id import IdView
from padinfo.view.monster_list import MonsterListView, MonsterListViewState


class MonsterListPaneNames:
    home = 'home'
    refresh = 'refresh'
    reset = 'reset'


class MonsterListMenu:
    MENU_TYPE = 'MonsterListMenu'
    CHILD_MENU_TYPE = 'IdMenu'

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = MonsterListMenu.monster_list_control
        embed = EmbedMenu(MonsterListMenuPanes.transitions(), initial_control)
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
        control = MonsterListMenu.monster_list_control(view_state)
        return control

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
    def monster_list_control(state: MonsterListViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [MonsterListView.embed(state)],
            reaction_list
        )

    @staticmethod
    def get_child_data(ims, emoji_clicked):
        emoji_response = IdMenuPanes.emoji_name_to_emoji(IdMenuPaneNames.refresh) \
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


class MonsterListMenuPanes(MenuPanes):
    INITIAL_EMOJI = MonsterListEmoji.home
    DATA = {
        # tuple parts: parent_response, pane_type, respond_with_child
        MonsterListEmoji.home: (MonsterListMenu.respond_with_monster_list, MonsterListPaneNames.home, False),
        MonsterListEmoji.zero: (None, IdView.VIEW_TYPE, True),
        MonsterListEmoji.one: (None, IdView.VIEW_TYPE, True),
        MonsterListEmoji.two: (None, IdView.VIEW_TYPE, True),
        MonsterListEmoji.three: (None, IdView.VIEW_TYPE, True),
        MonsterListEmoji.four: (None, IdView.VIEW_TYPE, True),
        MonsterListEmoji.five: (None, IdView.VIEW_TYPE, True),
        MonsterListEmoji.six: (None, IdView.VIEW_TYPE, True),
        MonsterListEmoji.seven: (None, IdView.VIEW_TYPE, True),
        MonsterListEmoji.eight: (None, IdView.VIEW_TYPE, True),
        MonsterListEmoji.nine: (None, IdView.VIEW_TYPE, True),
        MonsterListEmoji.ten: (None, IdView.VIEW_TYPE, True),
        MonsterListEmoji.refresh: (
            MonsterListMenu.respond_with_refresh, MonsterListPaneNames.refresh, False),
        MonsterListEmoji.reset: (
            MonsterListMenu.respond_with_reset, MonsterListPaneNames.reset, False)
    }
    HIDDEN_EMOJIS = [
        MonsterListPaneNames.home,
        MonsterListPaneNames.refresh,
        MonsterListPaneNames.reset,
    ]

    @classmethod
    def get_initial_reaction_list(cls, number_of_evos: int):
        return cls.emoji_names()[:number_of_evos]
