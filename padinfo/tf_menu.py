from typing import TYPE_CHECKING, Optional

from discord import Message
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji.emoji_cache import emoji_cache
from discordmenu.reaction_filter import ValidEmojiReactionFilter, NotPosterEmojiReactionFilter, \
    MessageOwnerReactionFilter, FriendReactionFilter, BotAuthoredMessageReactionFilter

from padinfo.view.id import IdView
from padinfo.view.transforminfo import TransformInfoView
from padinfo.view_state.id import IdViewState
from padinfo.view_state.transforminfo import TransformInfoViewState

if TYPE_CHECKING:
    pass

emoji_button_names = ['\N{HOUSE BUILDING}', '\N{DOWNWARDS BLACK ARROW}', '\N{UPWARDS BLACK ARROW}', '\N{CROSS MARK}']
menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')

class TransformInfoMenu:
    INITIAL_EMOJI = emoji_button_names[0]
    MENU_TYPE = 'TransformInfo'

    @staticmethod
    def menu(original_author_id, friend_ids, bot_id):
        transitions = {
            TransformInfoMenu.INITIAL_EMOJI: TransformInfoMenu.respond_to_house,
            emoji_button_names[1]: TransformInfoMenu.respond_to_down,
            emoji_button_names[2]: TransformInfoMenu.respond_to_up,
        }

        valid_emoji_names = [e.name for e in emoji_cache.custom_emojis] + list(transitions.keys())
        reaction_filters = [
            ValidEmojiReactionFilter(valid_emoji_names),
            NotPosterEmojiReactionFilter(),
            BotAuthoredMessageReactionFilter(bot_id),
            MessageOwnerReactionFilter(original_author_id, FriendReactionFilter(original_author_id, friend_ids))
        ]

        return EmbedMenu(reaction_filters, transitions, TransformInfoMenu.tf_control, menu_emoji_config)

    @staticmethod
    async def respond_to_down(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        ims['query'] = ims['b_query']
        ims['resolved_monster_id'] = None
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = TransformInfoMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_to_up(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        ims['query'] = ims['t_query']
        ims['resolved_monster_id'] = None
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = TransformInfoMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_to_house(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        tf_view_state = await TransformInfoViewState.deserialize(dgcog, user_config, ims)
        tf_control = TransformInfoMenu.tf_control(tf_view_state)
        return tf_control

    @staticmethod
    def tf_control(state: TransformInfoViewState):
        return EmbedControl(
            [TransformInfoView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def id_control(state: IdViewState):
        return EmbedControl(
            [IdView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )
