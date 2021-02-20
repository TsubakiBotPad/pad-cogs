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
    async def respond_with_delete(message: Message, ims, **data):
        return await message.delete()

    @staticmethod
    async def respond_with_n(message: Optional[Message], ims, _n, **data):
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


class SeriesScrollMenuPanes(MenuPanes):
    INITIAL_EMOJI = '\N{HOUSE BUILDING}'
    NON_MONSTER_EMOJI_COUNT = 5
    DATA = {
        # tuple parts: emoji, pane_type, respond_with_parent, respond_with_child
        SeriesScrollMenu.respond_with_delete: ('\N{CROSS MARK}', None, True, False),
        SeriesScrollMenu.respond_with_monster_list: (
            emoji_buttons[SeriesScrollPaneNames.home], SeriesScrollPaneNames.home, True, False),
        SeriesScrollMenu.respond_with_left: ('\N{LEFTWARDS BLACK ARROW}', SeriesScrollView.VIEW_TYPE, True, False),
        SeriesScrollMenu.respond_with_right: ('\N{BLACK RIGHTWARDS ARROW}', SeriesScrollView.VIEW_TYPE, True, False),
        SeriesScrollMenu.respond_with_up: (
            '\N{BLACK UP-POINTING DOUBLE TRIANGLE}', SeriesScrollView.VIEW_TYPE, True, False),
        SeriesScrollMenu.respond_with_down: (
            '\N{BLACK DOWN-POINTING DOUBLE TRIANGLE}', SeriesScrollView.VIEW_TYPE, True, False),
        SeriesScrollMenu.respond_with_0: (char_to_emoji('0'), IdView.VIEW_TYPE, False, True),
        SeriesScrollMenu.respond_with_1: (char_to_emoji('1'), IdView.VIEW_TYPE, False, True),
        SeriesScrollMenu.respond_with_2: (char_to_emoji('2'), IdView.VIEW_TYPE, False, True),
        SeriesScrollMenu.respond_with_3: (char_to_emoji('3'), IdView.VIEW_TYPE, False, True),
        SeriesScrollMenu.respond_with_4: (char_to_emoji('4'), IdView.VIEW_TYPE, False, True),
        SeriesScrollMenu.respond_with_5: (char_to_emoji('5'), IdView.VIEW_TYPE, False, True),
        SeriesScrollMenu.respond_with_6: (char_to_emoji('6'), IdView.VIEW_TYPE, False, True),
        SeriesScrollMenu.respond_with_7: (char_to_emoji('7'), IdView.VIEW_TYPE, False, True),
        SeriesScrollMenu.respond_with_8: (char_to_emoji('8'), IdView.VIEW_TYPE, False, True),
        SeriesScrollMenu.respond_with_9: (char_to_emoji('9'), IdView.VIEW_TYPE, False, True),
        SeriesScrollMenu.respond_with_10: (char_to_emoji('10'), IdView.VIEW_TYPE, False, True),
        SeriesScrollMenu.respond_with_refresh: (
            '\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}', SeriesScrollPaneNames.refresh, True, False),
        SeriesScrollMenu.respond_with_reset: (emoji_buttons['reset'], SeriesScrollPaneNames.reset, True, False)
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
