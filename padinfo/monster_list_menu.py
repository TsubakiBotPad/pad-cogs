from typing import TYPE_CHECKING, Optional

from discord import Message
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji.emoji_cache import emoji_cache
from discordmenu.reaction_filter import ValidEmojiReactionFilter, NotPosterEmojiReactionFilter, \
    MessageOwnerReactionFilter, FriendReactionFilter, BotAuthoredMessageReactionFilter
from tsutils import char_to_emoji

from padinfo.id_menu import IdMenu
from padinfo.pane_names import IdMenuPaneNames, MonsterListPaneNames, global_emoji_responses
from padinfo.reaction_list import get_id_menu_initial_reaction_list
from padinfo.view.id import IdView
from padinfo.view.monster_list import MonsterListView
from padinfo.view_state.id import IdViewState
from padinfo.view_state.monster_list import MonsterListViewState

if TYPE_CHECKING:
    pass

menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')


class MonsterListMenu:
    MENU_TYPE = 'MonsterListMenu'
    CHILD_MENU_TYPE = 'IdMenu'

    @staticmethod
    def menu(original_author_id, friend_ids, bot_id, initial_control=None):
        if initial_control is None:
            initial_control = MonsterListMenu.monster_list_control

        valid_emoji_names = [e.name for e in emoji_cache.custom_emojis] + list(MonsterListMenuPanes.emoji_names())
        reaction_filters = [
            ValidEmojiReactionFilter(valid_emoji_names),
            NotPosterEmojiReactionFilter(),
            BotAuthoredMessageReactionFilter(bot_id),
            MessageOwnerReactionFilter(original_author_id, FriendReactionFilter(original_author_id, friend_ids))
        ]
        embed = EmbedMenu(reaction_filters, MonsterListMenuPanes.transitions(), initial_control, menu_emoji_config)
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
    async def respond_with_n(message: Optional[Message], ims, n, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        ims['resolved_monster_id'] = int(ims['monster_list'][n])

        view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        control = MonsterListMenu.id_control(view_state)
        return control

    @staticmethod
    async def respond_with_eyes(message: Optional[Message], ims, **data):
        # the message we get here is the NEXT message, not the current one. The ims and everything else
        # is for the current message, but they should be identical.
        dgcog = data['dgcog']
        reaction_list = await get_id_menu_initial_reaction_list(None, dgcog, dgcog.database.graph.get_monster(
            int(ims['resolved_monster_id'])), force_evoscroll=True)
        if not data.get('child_message_ims'):
            # default to the overview screen if we weren't already on a screen
            ims['reaction_list'] = ','.join(reaction_list)
            ims['is_child'] = 'True'
            return await IdMenu.respond_with_current_id(message, ims, **data)
        data['child_message_ims']['reaction_list'] = ','.join(reaction_list)
        data['child_message_ims']['resolved_monster_id'] = int(ims['resolved_monster_id'])
        return await IdMenu.respond_with_refresh(message, data['child_message_ims'], **data)

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
        if MonsterListMenuPanes.emoji_name_to_emoji('expand') in reaction_list:
            reaction_list.pop(MonsterListMenuPanes.emoji_name_to_emoji('expand'))
        return EmbedControl(
            [MonsterListView.embed(state)],
            reaction_list
        )

    @staticmethod
    def id_control(state: IdViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        if MonsterListMenuPanes.emoji_name_to_emoji('expand') not in reaction_list:
            reaction_list.append(MonsterListMenuPanes.emoji_name_to_emoji('expand'))
        return EmbedControl(
            [IdView.embed(state)],
            reaction_list
        )


class MonsterListMenuPanes:
    INITIAL_EMOJI = '\N{HOUSE BUILDING}'
    DATA = {
        MonsterListMenu.respond_with_monster_list: ('\N{HOUSE BUILDING}', IdMenuPaneNames.evos),
        MonsterListMenu.respond_with_0: (char_to_emoji('0'), IdMenuPaneNames.id),
        MonsterListMenu.respond_with_1: (char_to_emoji('1'), IdMenuPaneNames.id),
        MonsterListMenu.respond_with_2: (char_to_emoji('2'), IdMenuPaneNames.id),
        MonsterListMenu.respond_with_3: (char_to_emoji('3'), IdMenuPaneNames.id),
        MonsterListMenu.respond_with_4: (char_to_emoji('4'), IdMenuPaneNames.id),
        MonsterListMenu.respond_with_5: (char_to_emoji('5'), IdMenuPaneNames.id),
        MonsterListMenu.respond_with_6: (char_to_emoji('6'), IdMenuPaneNames.id),
        MonsterListMenu.respond_with_7: (char_to_emoji('7'), IdMenuPaneNames.id),
        MonsterListMenu.respond_with_8: (char_to_emoji('8'), IdMenuPaneNames.id),
        MonsterListMenu.respond_with_9: (char_to_emoji('9'), IdMenuPaneNames.id),
        MonsterListMenu.respond_with_10: ('\N{KEYCAP TEN}', IdMenuPaneNames.id),
        MonsterListMenu.respond_with_eyes: ('\N{SQUARED ID}', MonsterListPaneNames.expand),
        MonsterListMenu.respond_with_refresh: (
            '\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}', MonsterListPaneNames.refresh),
        MonsterListMenu.respond_with_reset: (global_emoji_responses['reset'], MonsterListPaneNames.reset)
    }
    HIDDEN_EMOJIS = [
        MonsterListPaneNames.refresh,
        MonsterListPaneNames.reset,
    ]

    @classmethod
    def emoji_names(cls):
        return [v[0] for k, v in cls.DATA.items() if v[1] not in cls.HIDDEN_EMOJIS]

    @classmethod
    def transitions(cls):
        return {v[0]: k for k, v in cls.DATA.items()}

    @classmethod
    def pane_types(cls):
        return {v[1]: k for k, v in cls.DATA.items() if v[1] and v[1] not in cls.HIDDEN_EMOJIS}

    @staticmethod
    def get_initial_reaction_list(number_of_evos: int):
        return MonsterListMenuPanes.emoji_names()[:number_of_evos + 1]

    @staticmethod
    def emoji_name_to_emoji(name: str):
        for _, data_pair in MonsterListMenuPanes.DATA.items():
            if data_pair[1] == name:
                return data_pair[0]
        return None

    @staticmethod
    def emoji_name_to_function(name: str):
        for _, data_pair in MonsterListMenuPanes.DATA.items():
            if data_pair[1] == name:
                return data_pair[1]
        return None
