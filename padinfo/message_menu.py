from typing import TYPE_CHECKING, Optional

from discord import Message
from discordmenu.embed.control import EmbedControl
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu
from discordmenu.emoji.emoji_cache import emoji_cache
from discordmenu.reaction_filter import ValidEmojiReactionFilter, NotPosterEmojiReactionFilter, \
    MessageOwnerReactionFilter, FriendReactionFilter, BotAuthoredMessageReactionFilter

from padinfo.view.message_view import MessageView
from padinfo.view_state.message import MessageViewState

if TYPE_CHECKING:
    pass

menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')


class MessagePaneNames:
    home = 'home'


class MessageMenu:
    MENU_TYPE = 'MessageMenu'
    message = None

    @staticmethod
    def menu(original_author_id, friend_ids, bot_id):
        valid_emoji_names = [e.name for e in emoji_cache.custom_emojis] + list(MessageMenuPanes.emoji_names())
        reaction_filters = [
            ValidEmojiReactionFilter(valid_emoji_names),
            NotPosterEmojiReactionFilter(),
            BotAuthoredMessageReactionFilter(bot_id),
            MessageOwnerReactionFilter(original_author_id, FriendReactionFilter(original_author_id, friend_ids))
        ]
        embed = EmbedMenu(reaction_filters, MessageMenuPanes.transitions(), MessageMenu.message_control,
                          menu_emoji_config)
        return embed

    @staticmethod
    async def respond_with_message(message: Optional[Message], ims, **data):
        dgcog = data.get('dgcog')
        user_config = data.get('user_config')
        view_state = await MessageViewState.deserialize(dgcog, user_config, ims)
        control = MessageMenu.message_control(view_state)
        return control

    @staticmethod
    def message_control(state: MessageViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [MessageView.embed(state)],
            reaction_list
        )


class MessageMenuPanes:
    INITIAL_EMOJI = '\N{HOUSE BUILDING}'
    DATA = {
        MessageMenu.respond_with_message: ('\N{HOUSE BUILDING}', MessagePaneNames.home),

    }
    HIDDEN_EMOJIS = [
        MessagePaneNames.home,
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
        return MessageMenuPanes.emoji_names()[:number_of_evos]

    @staticmethod
    def emoji_name_to_emoji(name: str):
        for _, data_pair in MessageMenuPanes.DATA.items():
            if data_pair[1] == name:
                return data_pair[0]
        return None

    @staticmethod
    def emoji_name_to_function(name: str):
        for _, data_pair in MessageMenuPanes.DATA.items():
            if data_pair[1] == name:
                return data_pair[1]
        return None
