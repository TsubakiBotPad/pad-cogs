from typing import TYPE_CHECKING, Optional

from discord import Message
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji.emoji_cache import emoji_cache
from discordmenu.reaction_filter import ValidEmojiReactionFilter, NotPosterEmojiReactionFilter, \
    MessageOwnerReactionFilter, FriendReactionFilter, BotAuthoredMessageReactionFilter
from tsutils import char_to_emoji

from padinfo.view.id import IdView
from padinfo.view.materials import MaterialsView
from padinfo.view.otherinfo import OtherInfoView
from padinfo.view.pantheon import PantheonView
from padinfo.view.pic import PicView
from padinfo.view.evos import EvosView
from padinfo.view_state.evos import EvosViewState
from padinfo.view_state.id import IdViewState
from padinfo.view_state.materials import MaterialsViewState
from padinfo.view_state.otherinfo import OtherInfoViewState
from padinfo.view_state.pantheon import PantheonViewState
from padinfo.view_state.pic import PicViewState

if TYPE_CHECKING:
    pass

emoji_button_names = [
    # '\N{BLACK LEFT-POINTING TRIANGLE}',
    # '\N{BLACK RIGHT-POINTING TRIANGLE}',
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
    INITIAL_EMOJI = emoji_button_names[0]
    MENU_TYPE = 'IdMenu'

    @staticmethod
    def menu(original_author_id, friend_ids, bot_id):
        transitions = {
            # emoji_button_names[0]: respond_to_left,
            # emoji_button_names[1]: respond_to_right,
            IdMenu.INITIAL_EMOJI: IdMenu.respond_with_current_id,
            emoji_button_names[1]: IdMenu.respond_with_evos,
            emoji_button_names[2]: IdMenu.respond_with_mats,
            emoji_button_names[3]: IdMenu.respond_with_picture,
            emoji_button_names[4]: IdMenu.repond_with_pantheon,
            emoji_button_names[5]: IdMenu.respond_with_otherinfo,
        }

        valid_emoji_names = [e.name for e in emoji_cache.custom_emojis] + list(transitions.keys())
        reaction_filters = [
            ValidEmojiReactionFilter(valid_emoji_names),
            NotPosterEmojiReactionFilter(),
            BotAuthoredMessageReactionFilter(bot_id),
            MessageOwnerReactionFilter(original_author_id, FriendReactionFilter(original_author_id, friend_ids))
        ]
        embed = EmbedMenu(reaction_filters, transitions, IdMenu.id_control, menu_emoji_config)
        return embed

    @staticmethod
    async def respond_to_left(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        # Extract the query from the id state
        # TODO: let the user switch scroll modes in between then and now
        ims['query'] = ims['left_arrow']
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = IdMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_to_right(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        # Extract the query from the id state
        # TODO: let the user switch scroll modes in between then and now
        ims['query'] = ims['right_arrow']
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = IdMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def _deserialize_appropriately(ims, menu_type):
        # need to deserialize the left-right arrows according to which type of tab we're in
        # but I think this means maybe type needs to be a function of tab not of overall menu?
        # unclear
        pass

    @staticmethod
    async def respond_with_current_id(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.id_control(view_state)
        return control

    @staticmethod
    async def respond_with_evos(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await EvosViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.evos_control(view_state)
        return control

    @staticmethod
    async def respond_with_mats(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await MaterialsViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.mats_control(view_state)
        return control

    @staticmethod
    async def respond_with_picture(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await PicViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.pic_control(view_state)
        return control

    @staticmethod
    async def repond_with_pantheon(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await PantheonViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.pantheon_control(view_state)
        return control

    @staticmethod
    async def respond_with_otherinfo(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await OtherInfoViewState.deserialize(dgcog, user_config, ims)
        control = IdMenu.otherinfo_control(view_state)
        return control

    @staticmethod
    def id_control(state: IdViewState):
        return EmbedControl(
            [IdView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def evos_control(state: EvosViewState):
        return EmbedControl(
            [EvosView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def mats_control(state: MaterialsViewState):
        return EmbedControl(
            [MaterialsView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def pic_control(state: PicViewState):
        return EmbedControl(
            [PicView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def pantheon_control(state: PantheonViewState):
        return EmbedControl(
            [PantheonView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

    @staticmethod
    def otherinfo_control(state: OtherInfoViewState):
        return EmbedControl(
            [OtherInfoView.embed(state)],
            [emoji_cache.get_by_name(e) for e in emoji_button_names]
        )

