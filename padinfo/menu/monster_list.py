from typing import List, Optional, Type

from discord import Message
from discordmenu.embed.menu import EmbedControl, EmbedMenu
from tsutils.emoji import char_to_emoji
from tsutils.menu.components.panes import MenuPanes, emoji_buttons

from padinfo.menu.id import IdMenu, IdMenuEmoji
from padinfo.menu.na_diff import NaDiffEmoji, NaDiffMenu
from padinfo.view.id import IdView
from padinfo.view.monster_list.all_mats import AllMatsViewState
from padinfo.view.monster_list.id_search import IdSearchViewState
from padinfo.view.monster_list.monster_list import MonsterListView, MonsterListViewState
from padinfo.view.monster_list.scroll import ScrollViewState, ScrollView
from padinfo.view.monster_list.static_monster_list import StaticMonsterListViewState


class MonsterListEmoji:
    delete = '\N{CROSS MARK}'
    home = emoji_buttons['home']
    prev_page = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
    prev_mon = '\N{BLACK LEFT-POINTING TRIANGLE}'
    next_mon = '\N{BLACK RIGHT-POINTING TRIANGLE}'
    next_page = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'
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

    view_state_types = {
        AllMatsViewState.VIEW_STATE_TYPE: AllMatsViewState,
        IdSearchViewState.VIEW_STATE_TYPE: IdSearchViewState,
        StaticMonsterListViewState.VIEW_STATE_TYPE: StaticMonsterListViewState,
        ScrollViewState.VIEW_STATE_TYPE: ScrollViewState,
    }

    view_types = {
        ScrollViewState.VIEW_STATE_TYPE: ScrollView
    }

    child_menu_type_to_emoji_response_map = {
        IdMenu.MENU_TYPE: IdMenuEmoji.refresh,
        NaDiffMenu.MENU_TYPE: NaDiffEmoji.home
    }

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = MonsterListMenu.monster_list_control
        embed = EmbedMenu(MonsterListMenuPanes.transitions(), initial_control)
        return embed

    @classmethod
    async def _get_view_state(cls, ims: dict, **data) -> MonsterListViewState:
        dbcog = data['dbcog']
        user_config = data['user_config']
        view_state_class = cls.view_state_types[ims['menu_type']]
        return await view_state_class.deserialize(dbcog, user_config, ims)

    @classmethod
    def _get_view(cls, state: MonsterListViewState) -> Type[MonsterListView]:
        return cls.view_types.get(state.VIEW_STATE_TYPE) or MonsterListView

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

    @classmethod
    async def respond_with_left(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        view_state.decrement_page()
        return MonsterListMenu.monster_list_control(view_state)

    @classmethod
    async def respond_with_right(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        view_state.increment_page()
        return MonsterListMenu.monster_list_control(view_state)

    @classmethod
    async def respond_with_monster_list(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        return MonsterListMenu.monster_list_control(view_state)

    @classmethod
    async def respond_with_previous_monster(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        await view_state.decrement_index(data['dbcog'])
        return MonsterListMenu.monster_list_control(view_state)

    @classmethod
    async def respond_with_next_monster(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        await view_state.increment_index(data['dbcog'])
        return MonsterListMenu.monster_list_control(view_state)

    @staticmethod
    async def respond_with_delete(message: Message, ims, **data):
        return await message.delete()

    @staticmethod
    async def respond_with_n(message: Optional[Message], ims, n, **data):
        ims['current_index'] = n
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

    @classmethod
    def monster_list_control(cls, state: MonsterListViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        view_type = cls._get_view(state)
        return EmbedControl(
            [view_type.embed(state)],
            reaction_list
        )

    @classmethod
    async def click_child_number(cls, ims, emoji_clicked, **data):
        if not MonsterListMenuPanes.respond_to_emoji_with_child(emoji_clicked):
            return None, {}
        n = MonsterListMenuPanes.emoji_names().index(emoji_clicked)
        view_state = await cls._get_view_state(ims, **data)
        view_state.set_index(MonsterListMenuPanes.get_monster_index(n))
        extra_ims = view_state.get_serialized_child_extra_ims()
        emoji_response = cls.child_menu_type_to_emoji_response_map[view_state.child_menu_type]
        return emoji_response, extra_ims

    @classmethod
    async def auto_scroll_child_left(cls, ims, _emoji_clicked, **data):
        view_state = await cls._get_view_state(ims, **data)
        return await MonsterListMenu._scroll_child(view_state, view_state.decrement_index, data['dbcog'])

    @classmethod
    async def auto_scroll_child_right(cls, ims, _emoji_clicked, **data):
        view_state = await cls._get_view_state(ims, **data)
        return await MonsterListMenu._scroll_child(view_state, view_state.increment_index, data['dbcog'])

    @classmethod
    async def _scroll_child(cls, view_state: MonsterListViewState, update_function, dbcog):
        # when the parent ims updated, it was a deepcopy of the ims / view_state we have now,
        # so we have to redo the update function that we did before
        await update_function(dbcog)
        extra_ims = view_state.get_serialized_child_extra_ims()
        emoji_response = cls.child_menu_type_to_emoji_response_map[view_state.child_menu_type]
        return emoji_response, extra_ims


class MonsterListMenuPanes(MenuPanes):
    INITIAL_EMOJI = MonsterListEmoji.home
    NON_MONSTER_EMOJI_COUNT = 5
    DATA = {
        # tuple parts: parent_response, pane_type, respond_with_child
        MonsterListEmoji.delete: (MonsterListMenu.respond_with_delete, None, None),
        MonsterListEmoji.home: (MonsterListMenu.respond_with_monster_list, MonsterListEmoji.home, None),
        MonsterListEmoji.prev_page: (MonsterListMenu.respond_with_left, MonsterListView.VIEW_TYPE, None),
        MonsterListEmoji.prev_mon: (
            MonsterListMenu.respond_with_previous_monster, None, MonsterListMenu.auto_scroll_child_left),
        MonsterListEmoji.next_mon: (
            MonsterListMenu.respond_with_next_monster, None, MonsterListMenu.auto_scroll_child_right),
        MonsterListEmoji.next_page: (MonsterListMenu.respond_with_right, MonsterListView.VIEW_TYPE, None),
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
        return cls.emoji_names()[:number_of_evos + cls.NON_MONSTER_EMOJI_COUNT]

    @classmethod
    def get_previous_reaction_list_num_monsters(cls, reaction_list: List):
        return len(reaction_list) - cls.NON_MONSTER_EMOJI_COUNT

    @classmethod
    def get_monster_index(cls, n: int):
        return n - cls.NON_MONSTER_EMOJI_COUNT
