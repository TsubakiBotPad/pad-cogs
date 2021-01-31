from typing import TYPE_CHECKING

from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji_cache import emoji_cache
from discordmenu.reaction_filter import ValidEmojiReactionFilter, NotPosterEmojiReactionFilter, \
    MessageOwnerReactionFilter
from tsutils import char_to_emoji

from padinfo.view.id import IdView
from padinfo.view.leader_skill import LeaderSkillView
from padinfo.view_state.id import IdViewState
from padinfo.view_state.leader_skill import LeaderSkillViewState

if TYPE_CHECKING:
    pass

emoji_button_names = ['\N{HOUSE BUILDING}', char_to_emoji('l'), char_to_emoji('r')]


class LeaderSkillMenu:
    INITIAL_EMOJI = emoji_button_names[0]
    MENU_TYPE = 'LeaderSkill'

    @staticmethod
    def menu(original_author_id):
        panes = {
            LeaderSkillMenu.INITIAL_EMOJI: LeaderSkillMenu.ls_embed,
            emoji_button_names[1]: LeaderSkillMenu.id_embed,
            emoji_button_names[2]: LeaderSkillMenu.id_embed,
        }

        valid_emoji_names = [e.name for e in emoji_cache.custom_emojis] + list(panes.keys())
        reaction_filters = [
            ValidEmojiReactionFilter(valid_emoji_names),
            NotPosterEmojiReactionFilter(),
            MessageOwnerReactionFilter(original_author_id)
        ]

        return EmbedMenu(reaction_filters, panes)

    @staticmethod
    def ls_embed(prev_embed_control, **state):
        return EmbedControl(
            [LeaderSkillView.embed(**state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def id_embed(prev_embed_control, **state):
        return EmbedControl(
            [IdView.embed(**state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

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
