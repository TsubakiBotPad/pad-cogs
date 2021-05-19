from copy import deepcopy
from typing import Optional, List

from discord import Message
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from tsutils import char_to_emoji

from tsutils.menu.panes import emoji_buttons, MenuPanes
from padinfo.menu.id import IdMenu, IdMenuPanes, IdMenuEmoji
from padinfo.view.id import IdView
from padinfo.view.monster_list import MonsterListView, MonsterListViewState


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
    async def respond_with_left(message: Optional[Message], ims, **data):
        current_page = ims['current_page']
        if current_page > 0:
            ims['current_page'] = current_page - 1
            ims['current_index'] = None
            return await MonsterListMenu.respond_with_monster_list(message, ims, **data)
        paginated_monsters = MonsterListViewState.query_from_ims(data['dgcog'], ims)
        ims['current_page'] = len(paginated_monsters) - 1
        ims['current_index'] = None
        return await MonsterListMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_right(message: Optional[Message], ims, **data):
        paginated_monsters = MonsterListViewState.query_from_ims(data['dgcog'], ims)
        current_page = ims['current_page']
        if current_page < len(paginated_monsters) - 1:
            ims['current_page'] = current_page + 1
            ims['current_index'] = None
            return await MonsterListMenu.respond_with_monster_list(message, ims, **data)
        ims['current_page'] = 0
        ims['current_index'] = None
        return await MonsterListMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_monster_list(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        view_state = await MonsterListViewState.deserialize(dgcog, user_config, ims)
        control = MonsterListMenu.monster_list_control(view_state)
        return control

    @staticmethod
    async def respond_with_previous_monster(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        MonsterListMenu._update_ims_prev(dgcog, ims)
        return await MonsterListMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    def _update_ims_prev(dgcog, ims):
        current_index = ims['current_index']
        page = ims['current_page']
        paginated_monsters = MonsterListViewState.query_from_ims(dgcog, ims)
        max_index = len(paginated_monsters[page]) - 1
        if current_index is None:
            ims['current_index'] = max_index
            return
        if current_index > 0:
            ims['current_index'] = current_index - 1
            return
        if current_index == 0 and page > 0:
            ims['current_page'] = page - 1
            ims['current_index'] = MonsterListViewState.MAX_ITEMS_PER_PANE
            return
        if current_index == 0:
            # respond with left but then set the current index to the max thing possible
            ims['current_page'] = len(paginated_monsters) - 1
            ims['current_index'] = len(paginated_monsters[-1]) - 1

    @staticmethod
    async def respond_with_next_monster(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        MonsterListMenu._update_ims_next(dgcog, ims)
        return await MonsterListMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    def _update_ims_next(dgcog, ims):
        current_index = ims['current_index']
        page = ims['current_page']
        paginated_monsters = MonsterListViewState.query_from_ims(dgcog, ims)
        max_index = len(paginated_monsters[page]) - 1
        if current_index is None:
            ims['current_index'] = 0
            return
        if current_index < max_index:
            ims['current_index'] = current_index + 1
            return
        if current_index == max_index and page < len(paginated_monsters) - 1:
            ims['current_page'] = page + 1
            ims['current_index'] = 0
            return
        if current_index == max_index:
            ims['current_page'] = 0
            ims['current_index'] = 0

    @staticmethod
    async def respond_with_delete(message: Message, ims, **data):
        return await message.delete()

    @staticmethod
    async def respond_with_n(message: Optional[Message], ims, n, **data):
        ims['current_index'] =n
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
    def click_child_number(ims, emoji_clicked, **data):
        dgcog = data['dgcog']
        emoji_response = IdMenuEmoji.refresh \
            if MonsterListMenuPanes.respond_to_emoji_with_child(emoji_clicked) else None
        if emoji_response is None:
            return None, {}
        n = MonsterListMenuPanes.emoji_names().index(emoji_clicked)
        paginated_monsters = MonsterListViewState.query_from_ims(dgcog, ims)
        page = ims.get('current_page') or 0
        monster_list = paginated_monsters[page]
        extra_ims = {
            'is_child': True,
            'reaction_list': IdMenuPanes.emoji_names(),
            'menu_type': IdMenu.MENU_TYPE,
            'resolved_monster_id':
                monster_list[n - MonsterListMenuPanes.NON_MONSTER_EMOJI_COUNT].monster_id,
        }
        return emoji_response, extra_ims

    @staticmethod
    def auto_scroll_child_left(ims, _emoji_clicked, **data):
        return MonsterListMenu._scroll_child(ims, MonsterListMenu._update_ims_prev, **data)

    @staticmethod
    def auto_scroll_child_right(ims, _emoji_clicked, **data):
        return MonsterListMenu._scroll_child(ims, MonsterListMenu._update_ims_next, **data)

    @staticmethod
    def _scroll_child(ims, update_fn, **data):
        dgcog = data['dgcog']
        copy_ims = deepcopy(ims)
        update_fn(dgcog, copy_ims)
        paginated_monsters = MonsterListViewState.query_from_ims(dgcog, copy_ims)
        page = copy_ims.get('current_page') or 0
        monster_list = paginated_monsters[page]
        # after we figure out new rarity
        extra_ims = {
            'is_child': True,
            'reaction_list': IdMenuPanes.emoji_names(),
            'menu_type': IdMenu.MENU_TYPE,
            'resolved_monster_id': monster_list[copy_ims['current_index']].monster_id,
        }
        return IdMenuEmoji.refresh, extra_ims


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
