from typing import Optional, List

from discord import Message
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from tsutils import char_to_emoji

from padinfo.menu.common import emoji_buttons, MenuPanes
from padinfo.menu.id import IdMenu, IdMenuPanes, IdMenuPaneNames
from padinfo.view.id import IdView
from padinfo.view.series_scroll import SeriesScrollView, SeriesScrollViewState


class SeriesScrollPaneNames:
    home = 'home'
    refresh = 'refresh'
    reset = 'reset'


def _get_min_index(ims):
    return ims['current_min_index'].get(str(ims['rarity'])) or 0


def _set_min_index(ims, val):
    ims['current_min_index'][str(ims['rarity'])] = val


def _get_cur_index(ims):
    if ims.get('current_index') is None:
        return None
    return ims['current_index'].get(str(ims['rarity'])) or 0


def _set_cur_index(ims, val):
    if ims['current_index'] is None:
        ims['current_index'] = {}
    ims['current_index'][str(ims['rarity'])] = val


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

    @staticmethod
    async def respond_with_left(message: Optional[Message], ims, **data):
        current_rarity_index = ims['all_rarities'].index(ims['rarity'])
        ims['rarity'] = ims['all_rarities'][current_rarity_index - 1]
        return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_right(message: Optional[Message], ims, **data):
        current_rarity_index = ims['all_rarities'].index(ims['rarity'])
        if current_rarity_index == len(ims['all_rarities']) - 1:
            ims['rarity'] = ims['all_rarities'][0]
        else:
            ims['rarity'] = ims['all_rarities'][current_rarity_index + 1]
        if data.get('current_index_update') is not None:
            _set_cur_index(ims, data.get('current_index_update'))
        return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_up(message: Optional[Message], ims, **data):
        _set_min_index(ims, max(_get_min_index(ims) - SeriesScrollMenu.SCROLL_INTERVAL, 0))
        return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_down(message: Optional[Message], ims, **data):
        attempted_new_index = _get_min_index(ims) + SeriesScrollMenu.SCROLL_INTERVAL
        if attempted_new_index < len(ims['full_monster_list']):
            _set_min_index(ims, attempted_new_index)
        return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_monster_list(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        view_state = await SeriesScrollViewState.deserialize(dgcog, user_config, ims)
        control = SeriesScrollMenu.monster_list_control(view_state)
        return control

    @staticmethod
    async def respond_with_lazy_previous(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        current_index = _get_cur_index(ims)
        min_index, max_index = SeriesScrollViewState.get_current_indices(dgcog, ims)
        print('min_index', min_index)
        print('max_index', max_index)
        if current_index is None:
            _set_cur_index(ims, max_index)
            return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)
        if current_index < min_index or current_index > max_index:
            _set_cur_index(ims, max_index)
            return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)
        if current_index > min_index:
            _set_cur_index(ims, current_index - 1)
            return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)
        if current_index == min_index and min_index > 0:
            _set_cur_index(ims, current_index - 1)
            return await SeriesScrollMenu.respond_with_up(message, ims, **data)
        if current_index == 0:
            # respond with left but then set the current index to the max thing possible
            current_rarity_index = ims['all_rarities'].index(ims['rarity'])
            ims['rarity'] = ims['all_rarities'][current_rarity_index - 1]
            _set_cur_index(ims, len(SeriesScrollViewState.query_from_ims(dgcog, ims)) - 1)
            return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)
        return None

    @staticmethod
    async def respond_with_lazy_next(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        current_index = _get_cur_index(ims)
        min_index, max_index = SeriesScrollViewState.get_current_indices(dgcog, ims)
        print('min_index', min_index)
        print('max_index', max_index)
        if current_index is None:
            _set_cur_index(ims, min_index)
            return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)
        if current_index < min_index or current_index > max_index:
            _set_cur_index(ims, min_index)
            return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)
        if current_index < max_index:
            _set_cur_index(ims, current_index + 1)
            return await SeriesScrollMenu.respond_with_monster_list(message, ims, **data)
        full_monster_list = SeriesScrollViewState.query_from_ims(dgcog, ims)
        if current_index == max_index and max_index < len(full_monster_list) - 1:
            _set_cur_index(ims, current_index + 1)
            return await SeriesScrollMenu.respond_with_down(message, ims, **data)
        if current_index == len(full_monster_list) - 1:
            data['current_index_update'] = 0
            return await SeriesScrollMenu.respond_with_right(message, ims, **data)

        return None

    @staticmethod
    async def respond_with_delete(message: Message, ims, **data):
        return await message.delete()

    @staticmethod
    async def respond_with_n(message: Optional[Message], ims, n, **data):
        _set_cur_index(ims, _get_min_index(ims) + n)
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

    @staticmethod
    def get_child_data(ims, emoji_clicked):
        emoji_response = IdMenuPanes.emoji_name_to_emoji(IdMenuPaneNames.refresh) \
            if SeriesScrollMenuPanes.respond_to_emoji_with_child(emoji_clicked) else None
        if emoji_response is None:
            return None, {}
        n = SeriesScrollMenuPanes.emoji_names().index(emoji_clicked)
        extra_ims = {
            'is_child': True,
            'resolved_monster_id': int(
                ims['full_monster_list'][n + _get_min_index(ims) - SeriesScrollMenuPanes.NON_MONSTER_EMOJI_COUNT]),
            'reaction_list': IdMenuPanes.emoji_names(),
            'menu_type': IdMenu.MENU_TYPE,
        }
        return emoji_response, extra_ims


class SeriesScrollEmoji:
    delete = '\N{CROSS MARK}'
    home = emoji_buttons['home']
    rarity_left = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
    rarity_right = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'
    up = '\N{BLACK UP-POINTING DOUBLE TRIANGLE}'
    down = '\N{BLACK DOWN-POINTING DOUBLE TRIANGLE}'
    lazy_left = '\N{NORTH WEST ARROW}\N{VARIATION SELECTOR-16}'
    lazy_right = '\N{SOUTH EAST ARROW}\N{VARIATION SELECTOR-16}'
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


class SeriesScrollMenuPanes(MenuPanes):
    INITIAL_EMOJI = '\N{HOUSE BUILDING}'
    NON_MONSTER_EMOJI_COUNT = 7
    DATA = {
        # tuple parts: emoji, pane_type, respond_with_parent, respond_with_child
        SeriesScrollEmoji.delete: (SeriesScrollMenu.respond_with_delete, None, False),
        SeriesScrollEmoji.home: (SeriesScrollMenu.respond_with_monster_list, SeriesScrollPaneNames.home, False),
        SeriesScrollEmoji.rarity_left: (SeriesScrollMenu.respond_with_left, SeriesScrollView.VIEW_TYPE, False),
        SeriesScrollEmoji.rarity_right: (SeriesScrollMenu.respond_with_right, SeriesScrollView.VIEW_TYPE, False),
        SeriesScrollEmoji.up: (SeriesScrollMenu.respond_with_up, SeriesScrollView.VIEW_TYPE, False),
        SeriesScrollEmoji.down: (SeriesScrollMenu.respond_with_down, SeriesScrollView.VIEW_TYPE, False),
        SeriesScrollEmoji.lazy_left: (SeriesScrollMenu.respond_with_lazy_previous, None, True),
        SeriesScrollEmoji.lazy_right: (SeriesScrollMenu.respond_with_lazy_next, None, True),
        SeriesScrollEmoji.zero: (SeriesScrollMenu.respond_with_0, IdView.VIEW_TYPE, True),
        SeriesScrollEmoji.one: (SeriesScrollMenu.respond_with_1, IdView.VIEW_TYPE, True),
        SeriesScrollEmoji.two: (SeriesScrollMenu.respond_with_2, IdView.VIEW_TYPE, True),
        SeriesScrollEmoji.three: (SeriesScrollMenu.respond_with_3, IdView.VIEW_TYPE, True),
        SeriesScrollEmoji.four: (SeriesScrollMenu.respond_with_4, IdView.VIEW_TYPE, True),
        SeriesScrollEmoji.five: (SeriesScrollMenu.respond_with_5, IdView.VIEW_TYPE, True),
        SeriesScrollEmoji.six: (SeriesScrollMenu.respond_with_6, IdView.VIEW_TYPE, True),
        SeriesScrollEmoji.seven: (SeriesScrollMenu.respond_with_7, IdView.VIEW_TYPE, True),
        SeriesScrollEmoji.eight: (SeriesScrollMenu.respond_with_8, IdView.VIEW_TYPE, True),
        SeriesScrollEmoji.nine: (SeriesScrollMenu.respond_with_9, IdView.VIEW_TYPE, True),
        SeriesScrollEmoji.ten: (SeriesScrollMenu.respond_with_10, IdView.VIEW_TYPE, True),
        SeriesScrollEmoji.refresh: (
            SeriesScrollMenu.respond_with_refresh, SeriesScrollPaneNames.refresh, False),
        SeriesScrollEmoji.reset: (
            SeriesScrollMenu.respond_with_reset, SeriesScrollPaneNames.reset, False)
    }
    HIDDEN_EMOJIS = [
        SeriesScrollPaneNames.home,
        SeriesScrollPaneNames.refresh,
        SeriesScrollPaneNames.reset,
    ]

    @classmethod
    def get_initial_reaction_list(cls, number_of_evos: int):
        return cls.emoji_names()[:number_of_evos + cls.NON_MONSTER_EMOJI_COUNT]

    @classmethod
    def get_previous_reaction_list_num_monsters(cls, reaction_list: List):
        return len(reaction_list) - cls.NON_MONSTER_EMOJI_COUNT
