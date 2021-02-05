from typing import TYPE_CHECKING, Optional

from discord import Message
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji.emoji_cache import emoji_cache
from discordmenu.reaction_filter import ValidEmojiReactionFilter, NotPosterEmojiReactionFilter, \
    MessageOwnerReactionFilter, FriendReactionFilter, BotAuthoredMessageReactionFilter
from tsutils import char_to_emoji

from padinfo.view.id import IdView
from padinfo.view.materials import MaterialView
from padinfo.view.otherinfo import OtherInfoView
from padinfo.view.pantheon import PantheonView
from padinfo.view.pic import PicsView
from padinfo.view.evos import EvosView
from padinfo.view_state.id import IdViewState

if TYPE_CHECKING:
    pass

emoji_button_names = [
    '\N{BLACK LEFT-POINTING TRIANGLE}',
    '\N{BLACK RIGHT-POINTING TRIANGLE}',
    '\N{HOUSE BUILDING}',
    char_to_emoji('e'),
    '\N{MEAT ON BONE}',
    '\N{FRAME WITH PICTURE}',
    '\N{CLASSICAL BUILDING}',
    '\N{SCROLL}',
    '\N{CROSS MARK}',
]
menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')


class IdMenu:
    INITIAL_EMOJI = emoji_button_names[2]
    MENU_TYPE = 'IdMenu'

    @classmethod
    def menu(cls, original_author_id, friend_ids, bot_id):
        transitions = {
            cls.INITIAL_EMOJI: cls.respond_to_left,
            emoji_button_names[1]: cls.respond_to_right,
            emoji_button_names[2]: cls.respond_to_house,
            emoji_button_names[3]: cls.respond_to_e,
            # emoji_button_names[4]: cls.respond_to_bone,
            # emoji_button_names[5]: cls.respond_to_e,
            # emoji_button_names[6]: cls.respond_to_picture,
            # emoji_button_names[7]: cls.respond_to_building,
            # emoji_button_names[8]: cls.respond_to_scroll,
        }

        valid_emoji_names = [e.name for e in emoji_cache.custom_emojis] + list(transitions.keys())
        reaction_filters = [
            ValidEmojiReactionFilter(valid_emoji_names),
            NotPosterEmojiReactionFilter(),
            BotAuthoredMessageReactionFilter(bot_id),
            MessageOwnerReactionFilter(original_author_id, FriendReactionFilter(original_author_id, friend_ids))
        ]

        return EmbedMenu(reaction_filters, transitions, cls.id_control, menu_emoji_config)

    @classmethod
    async def respond_to_left(cls, message: Message, ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        # Extract the query from the id state
        # TODO: let the user switch scroll modes in between then and now
        ims['query'] = ims['left_arrow']
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = cls.id_control(id_view_state)
        return id_control

    @classmethod
    async def respond_to_right(cls, message: Message, ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        # Extract the query from the id state
        # TODO: let the user switch scroll modes in between then and now
        ims['query'] = ims['right_arrow']
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = cls.id_control(id_view_state)
        return id_control

    @classmethod
    async def respond_to_house(cls, message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = cls.id_control(id_view_state)
        return id_control

    @classmethod
    async def respond_to_e(cls, message: Message, ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = cls.evos_control(id_view_state)
        return id_control

    @classmethod
    async def respond_to_bone(cls, message: Message, ims, **data):
        pass

    @classmethod
    async def respond_to_picture(cls, message: Message, ims, **data):
        pass

    @classmethod
    async def respond_to_building(cls, message: Message, ims, **data):
        pass

    @classmethod
    async def respond_to_scroll(cls, message: Message, ims, **data):
        pass

    @staticmethod
    def evos_control(state: IdViewState):
        return EmbedControl(
            [EvosView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def id_control(state: IdViewState):
        return EmbedControl(
            [IdView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def mats_control(state: IdViewState):
        return EmbedControl(
            [MaterialView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def pantheon_control(state: IdViewState):
        return EmbedControl(
            [PantheonView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def otherinfo_view(state: IdViewState):
        return EmbedControl(
            [OtherInfoView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def pic_control(state: IdViewState):
        return EmbedControl(
            [PicsView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

