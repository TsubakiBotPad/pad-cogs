from typing import TYPE_CHECKING, Optional

from discord import Message
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji.emoji_cache import emoji_cache
from discordmenu.reaction_filter import ValidEmojiReactionFilter, NotPosterEmojiReactionFilter, \
    MessageOwnerReactionFilter, FriendReactionFilter, BotAuthoredMessageReactionFilter

from padinfo.view.id import IdView
from padinfo.view.leader_skill_single import LeaderSkillSingleView
from padinfo.view_state.id import IdViewState
from padinfo.view_state.leader_skill_single import LeaderSkillSingleViewState

if TYPE_CHECKING:
    pass

menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')


class LeaderSkillSingleMenu:
    EMOJI_BUTTON_NAMES = ('\N{HOUSE BUILDING}', '\N{SQUARED ID}', '\N{CROSS MARK}')
    MENU_TYPE = 'LeaderSkillSingle'

    @classmethod
    def menu(cls, original_author_id, friend_ids, bot_id):
        transitions = {
            cls.EMOJI_BUTTON_NAMES[0]: cls.respond_to_house,
            cls.EMOJI_BUTTON_NAMES[1]: cls.view_ls,
        }

        valid_emoji_names = [e.name for e in emoji_cache.custom_emojis] + list(transitions.keys())
        reaction_filters = [
            ValidEmojiReactionFilter(valid_emoji_names),
            NotPosterEmojiReactionFilter(),
            BotAuthoredMessageReactionFilter(bot_id),
            MessageOwnerReactionFilter(original_author_id, FriendReactionFilter(original_author_id, friend_ids))
        ]

        return EmbedMenu(reaction_filters, transitions, cls.ls_control, menu_emoji_config)

    @classmethod
    async def view_ls(cls, message: Optional[Message], ims, *, dgcog, user_config, **data):
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = cls.id_control(id_view_state)
        return id_control

    @classmethod
    async def respond_to_house(cls, message: Optional[Message], ims, *, dgcog, user_config, **data):
        ls_view_state = await LeaderSkillSingleViewState.deserialize(dgcog, user_config, ims)
        ls_control = cls.ls_control(ls_view_state)
        return ls_control

    @classmethod
    def ls_control(cls, state: LeaderSkillSingleViewState):
        return EmbedControl(
            [LeaderSkillSingleView.embed(state)],
            [emoji_cache.get_by_name(e) for e in cls.EMOJI_BUTTON_NAMES]
        )

    @classmethod
    def id_control(cls, state: IdViewState):
        return EmbedControl(
            [IdView.embed(state)],
            [emoji_cache.get_by_name(e) for e in cls.EMOJI_BUTTON_NAMES]
        )
