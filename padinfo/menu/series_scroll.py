from typing import Optional, List

from discord import Message
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from tsutils.emoji import char_to_emoji
from tsutils.menu.panes import MenuPanes, emoji_buttons

from padinfo.menu.id import IdMenu, IdMenuPanes, IdMenuEmoji
from padinfo.view.id import IdView
from padinfo.view.series_scroll import SeriesScrollView, SeriesScrollViewState


class SeriesScrollEmoji:
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


class SeriesScrollMenu:
    MENU_TYPE = 'SeriesScrollMenu'
    CHILD_MENU_TYPE = 'IdMenu'
    SCROLL_INTERVAL = SeriesScrollViewState.MAX_ITEMS_PER_PANE
    RARITY_INITIAL_TRY_ORDER = [6, 7, 8, 9, 10, 5, 4, 3, 11, 12, 2, 1, 13, 14]
    SCROLL_INITIAL_POSITION = 0

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = SeriesScrollMenu.monster_list_control
        embed = EmbedMenu(SeriesScrollMenuPanes.transitions(), initial_control)
        return embed

    @classmethod
    async def _get_view_state(cls, ims: dict, **data) -> SeriesScrollViewState:
        dbcog = data['dbcog']
        user_config = data['user_config']
        return await SeriesScrollViewState.deserialize(dbcog, user_config, ims)

    @staticmethod
    async def respond_with_refresh(message: Optional[Message], ims, **data):
        # this is only called once on message load
        if data.get('child_message_id'):
            ims['child_message_id'] = data['child_message_id']
        return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_reset(message: Optional[Message], ims, **data):
        # replace with the overview list after the child menu changes
        return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)

    @classmethod
    async def respond_with_left(cls, message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        view_state = await cls._get_view_state(ims, **data)
        await view_state.decrement_page(dbcog)
        return SeriesScrollMenu.monster_list_control(view_state)

    @classmethod
    async def respond_with_right(cls, message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        view_state = await cls._get_view_state(ims, **data)
        await view_state.increment_page(dbcog)
        return SeriesScrollMenu.monster_list_control(view_state)

    @classmethod
    async def respond_with_monster_list(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        return SeriesScrollMenu.monster_list_control(view_state)

    @classmethod
    async def respond_with_previous_monster(cls, message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        view_state = await cls._get_view_state(ims, **data)
        await view_state.decrement_index(dbcog)
        return SeriesScrollMenu.monster_list_control(view_state)

    @classmethod
    async def respond_with_next_monster(cls, message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        view_state = await cls._get_view_state(ims, **data)
        await view_state.increment_index(dbcog)
        return SeriesScrollMenu.monster_list_control(view_state)

    @staticmethod
    async def respond_with_delete(message: Message, ims, **data):
        return await message.delete()

    @classmethod
    async def respond_with_n(cls, message: Optional[Message], ims, n, **data):
        view_state = await cls._get_view_state(ims, **data)
        current_monster_list = view_state.paginated_monsters[view_state.current_page]
        # ims will be immediately be deserialized and shown, so don't change if n is out of range
        if n < len(current_monster_list):
            ims['current_index'] = n
        return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_0(message: Optional[Message], ims, **data):
        return await SeriesScrollMenu.respond_with_n(message, ims, 0, **data)

    @staticmethod
    async def respond_with_1(message: Optional[Message], ims, **data):
        return await SeriesScrollMenu.respond_with_n(message, ims, 1, **data)

    @staticmethod
    async def respond_with_2(message: Optional[Message], ims, **data):
        return await SeriesScrollMenu.respond_with_n(message, ims, 2, **data)

    @staticmethod
    async def respond_with_3(message: Optional[Message], ims, **data):
        return await SeriesScrollMenu.respond_with_n(message, ims, 3, **data)

    @staticmethod
    async def respond_with_4(message: Optional[Message], ims, **data):
        return await SeriesScrollMenu.respond_with_n(message, ims, 4, **data)

    @staticmethod
    async def respond_with_5(message: Optional[Message], ims, **data):
        return await SeriesScrollMenu.respond_with_n(message, ims, 5, **data)

    @staticmethod
    async def respond_with_6(message: Optional[Message], ims, **data):
        return await SeriesScrollMenu.respond_with_n(message, ims, 6, **data)

    @staticmethod
    async def respond_with_7(message: Optional[Message], ims, **data):
        return await SeriesScrollMenu.respond_with_n(message, ims, 7, **data)

    @staticmethod
    async def respond_with_8(message: Optional[Message], ims, **data):
        return await SeriesScrollMenu.respond_with_n(message, ims, 8, **data)

    @staticmethod
    async def respond_with_9(message: Optional[Message], ims, **data):
        return await SeriesScrollMenu.respond_with_n(message, ims, 9, **data)

    @staticmethod
    async def respond_with_10(message: Optional[Message], ims, **data):
        return await SeriesScrollMenu.respond_with_n(message, ims, 10, **data)

    @staticmethod
    def monster_list_control(state: SeriesScrollViewState):
        return EmbedControl(
            [SeriesScrollView.embed(state)],
            SeriesScrollMenuPanes.get_initial_reaction_list(state.max_len_so_far)
        )

    @classmethod
    async def click_child_number(cls, ims, emoji_clicked, **data):
        emoji_response = IdMenuEmoji.refresh \
            if SeriesScrollMenuPanes.respond_to_emoji_with_child(emoji_clicked) else None
        if emoji_response is None:
            return None, {}
        n = SeriesScrollMenuPanes.emoji_names().index(emoji_clicked)
        view_state = await cls._get_view_state(ims, **data)
        view_state.set_index(SeriesScrollMenuPanes.get_monster_index(n))
        extra_ims = view_state.get_serialized_child_extra_ims(IdMenuPanes.emoji_names(), IdMenu.MENU_TYPE)
        return emoji_response, extra_ims

    @classmethod
    async def auto_scroll_child_left(cls, ims, _emoji_clicked, **data):
        dbcog = data['dbcog']
        view_state = await cls._get_view_state(ims, **data)
        return await SeriesScrollMenu._scroll_child(view_state, view_state.decrement_index, dbcog)

    @classmethod
    async def auto_scroll_child_right(cls, ims, _emoji_clicked, **data):
        dbcog = data['dbcog']
        view_state = await cls._get_view_state(ims, **data)
        return await SeriesScrollMenu._scroll_child(view_state, view_state.increment_index, dbcog)

    @staticmethod
    async def _scroll_child(view_state: SeriesScrollViewState, update_fn, dbcog):
        await update_fn(dbcog)
        extra_ims = view_state.get_serialized_child_extra_ims(IdMenuPanes.emoji_names(), IdMenu.MENU_TYPE)
        return IdMenuEmoji.refresh, extra_ims


class SeriesScrollMenuPanes(MenuPanes):
    INITIAL_EMOJI = '\N{HOUSE BUILDING}'
    NON_MONSTER_EMOJI_COUNT = 5
    DATA = {
        # tuple parts: emoji, pane_type, respond_with_parent, respond_with_child
        SeriesScrollEmoji.delete: (SeriesScrollMenu.respond_with_delete, None, None),
        SeriesScrollEmoji.home: (SeriesScrollMenu.respond_with_monster_list, None, None),
        SeriesScrollEmoji.prev_page: (SeriesScrollMenu.respond_with_left, SeriesScrollView.VIEW_TYPE, None),
        SeriesScrollEmoji.prev_mon: (
            SeriesScrollMenu.respond_with_previous_monster, None, SeriesScrollMenu.auto_scroll_child_left),
        SeriesScrollEmoji.next_mon: (
            SeriesScrollMenu.respond_with_next_monster, None, SeriesScrollMenu.auto_scroll_child_right),
        SeriesScrollEmoji.next_page: (SeriesScrollMenu.respond_with_right, SeriesScrollView.VIEW_TYPE, None),
        SeriesScrollEmoji.zero: (
            SeriesScrollMenu.respond_with_0, IdView.VIEW_TYPE, SeriesScrollMenu.click_child_number),
        SeriesScrollEmoji.one: (
            SeriesScrollMenu.respond_with_1, IdView.VIEW_TYPE, SeriesScrollMenu.click_child_number),
        SeriesScrollEmoji.two: (
            SeriesScrollMenu.respond_with_2, IdView.VIEW_TYPE, SeriesScrollMenu.click_child_number),
        SeriesScrollEmoji.three: (
            SeriesScrollMenu.respond_with_3, IdView.VIEW_TYPE, SeriesScrollMenu.click_child_number),
        SeriesScrollEmoji.four: (
            SeriesScrollMenu.respond_with_4, IdView.VIEW_TYPE, SeriesScrollMenu.click_child_number),
        SeriesScrollEmoji.five: (
            SeriesScrollMenu.respond_with_5, IdView.VIEW_TYPE, SeriesScrollMenu.click_child_number),
        SeriesScrollEmoji.six: (
            SeriesScrollMenu.respond_with_6, IdView.VIEW_TYPE, SeriesScrollMenu.click_child_number),
        SeriesScrollEmoji.seven: (
            SeriesScrollMenu.respond_with_7, IdView.VIEW_TYPE, SeriesScrollMenu.click_child_number),
        SeriesScrollEmoji.eight: (
            SeriesScrollMenu.respond_with_8, IdView.VIEW_TYPE, SeriesScrollMenu.click_child_number),
        SeriesScrollEmoji.nine: (
            SeriesScrollMenu.respond_with_9, IdView.VIEW_TYPE, SeriesScrollMenu.click_child_number),
        SeriesScrollEmoji.ten: (
            SeriesScrollMenu.respond_with_10, IdView.VIEW_TYPE, SeriesScrollMenu.click_child_number),
        SeriesScrollEmoji.refresh: (SeriesScrollMenu.respond_with_refresh, None, None),
        SeriesScrollEmoji.reset: (SeriesScrollMenu.respond_with_reset, None, None)
    }
    HIDDEN_EMOJIS = [
        SeriesScrollEmoji.home,
        SeriesScrollEmoji.refresh,
        SeriesScrollEmoji.reset,
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
