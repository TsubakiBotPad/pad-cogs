from typing import TYPE_CHECKING, Optional

from discord import Message
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji.emoji_cache import emoji_cache
from discordmenu.reaction_filter import ValidEmojiReactionFilter, NotPosterEmojiReactionFilter, \
    MessageOwnerReactionFilter, FriendReactionFilter, BotAuthoredMessageReactionFilter
from tsutils import char_to_emoji

from padinfo.view.id import IdView
from padinfo.view.leader_skill import LeaderSkillView
from padinfo.view_state.id import IdViewState
from padinfo.view_state.leader_skill import LeaderSkillViewState

if TYPE_CHECKING:
    pass

emoji_button_names = ['\N{HOUSE BUILDING}', char_to_emoji('l'), char_to_emoji('r'), '\N{CROSS MARK}']
menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')


class LeaderSkillMenu:
    INITIAL_EMOJI = emoji_button_names[0]
    MENU_TYPE = 'LeaderSkill'

    @staticmethod
    def menu(original_author_id, friend_ids, bot_id):
        transitions = {
            LeaderSkillMenu.INITIAL_EMOJI: LeaderSkillMenu.respond_to_house,
            emoji_button_names[1]: LeaderSkillMenu.respond_to_l,
            emoji_button_names[2]: LeaderSkillMenu.respond_to_r,
        }

        valid_emoji_names = [e.name for e in emoji_cache.custom_emojis] + list(transitions.keys())
        reaction_filters = [
            ValidEmojiReactionFilter(valid_emoji_names),
            NotPosterEmojiReactionFilter(),
            BotAuthoredMessageReactionFilter(bot_id),
            MessageOwnerReactionFilter(original_author_id, FriendReactionFilter(original_author_id, friend_ids))
        ]

        return EmbedMenu(reaction_filters, transitions, LeaderSkillMenu.ls_control, menu_emoji_config)

    @staticmethod
    async def respond_to_r(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        # Extract the query from the ls state
        ims['query'] = ims['r_query']
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = LeaderSkillMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_to_l(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        # Extract the query from the ls state
        ims['query'] = ims['l_query']
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = LeaderSkillMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_to_house(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        ls_view_state = await LeaderSkillViewState.deserialize(dgcog, user_config, ims)
        ls_control = LeaderSkillMenu.ls_control(ls_view_state)
        return ls_control

    @staticmethod
    def ls_control(state: LeaderSkillViewState):
        return EmbedControl(
            [LeaderSkillView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def id_control(state: IdViewState):
        return EmbedControl(
            [IdView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )
