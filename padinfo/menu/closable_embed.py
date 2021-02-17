from discordmenu.embed.control import EmbedControl
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu
from discordmenu.emoji.emoji_cache import emoji_cache
from discordmenu.reaction_filter import ValidEmojiReactionFilter, NotPosterEmojiReactionFilter, \
    MessageOwnerReactionFilter, FriendReactionFilter, BotAuthoredMessageReactionFilter

from padinfo.view.id_traceback import IdTracebackView
from padinfo.view_state.closable_embed import ClosableEmbedViewState

menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')

view_types = {
    IdTracebackView.VIEW_TYPE: IdTracebackView
}


class ClosableEmbedMenu:
    MENU_TYPE = 'ClosableEmbedMenu'
    message = None

    @staticmethod
    def menu(original_author_id, friend_ids, bot_id):
        valid_emoji_names = [e.name for e in emoji_cache.custom_emojis]
        reaction_filters = [
            ValidEmojiReactionFilter(valid_emoji_names),
            NotPosterEmojiReactionFilter(),
            BotAuthoredMessageReactionFilter(bot_id),
            MessageOwnerReactionFilter(original_author_id, FriendReactionFilter(original_author_id, friend_ids))
        ]
        embed = EmbedMenu(reaction_filters, {}, ClosableEmbedMenu.message_control,
                          menu_emoji_config)
        return embed

    @staticmethod
    def message_control(state: ClosableEmbedViewState):
        view = view_types[state.view_type]
        return EmbedControl(
            [view.embed(state, **state.kwargs)],
            ['\N{CROSS MARK}']
        )
