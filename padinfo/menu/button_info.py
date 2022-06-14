from typing import Optional

from discord import Message
from discordmenu.embed.wrapper import EmbedWrapper
from discordmenu.embed.menu import EmbedMenu
from tsutils.emoji import char_to_emoji
from tsutils.menu.components.panes import MenuPanes, emoji_buttons

from padinfo.menu.components.evo_scroll_mixin import EvoScrollMenu
from padinfo.view.button_info import ButtonInfoOptions, ButtonInfoToggles, ButtonInfoView, ButtonInfoViewState


class ButtonInfoEmoji:
    left = '\N{BLACK LEFT-POINTING TRIANGLE}'
    right = '\N{BLACK RIGHT-POINTING TRIANGLE}'
    home = emoji_buttons['home']
    coop = ('coop_2p', '\N{BUSTS IN SILHOUETTE}')
    solo = ('solo_1p', '\N{BUST IN SILHOUETTE}')
    desktop = '\N{DESKTOP COMPUTER}'
    mobile = '\N{MOBILE PHONE}'
    limit_break = ('lv110', char_to_emoji('1'))
    super_limit_break = ('lv120', char_to_emoji('2'))


class ButtonInfoMenu(EvoScrollMenu):
    MENU_TYPE = 'ButtonInfo'
    VIEW_STATE_TYPE = ButtonInfoViewState

    @staticmethod
    def get_panes_type():
        #  TODO: change this to a property & classmethod once we update to Python 3.9
        return ButtonInfoMenuPanes

    @staticmethod
    def menu():
        return EmbedMenu(ButtonInfoMenuPanes.transitions(), ButtonInfoMenu.button_info_control)

    @classmethod
    async def _get_view_state(cls, ims: dict, **data) -> ButtonInfoViewState:
        dbcog = data['dbcog']
        user_config = data['user_config']
        return await ButtonInfoViewState.deserialize(dbcog, user_config, ims)

    @staticmethod
    async def respond_with_button_info(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']
        view_state = await ButtonInfoViewState.deserialize(dbcog, user_config, ims)
        control = ButtonInfoMenu.button_info_control(view_state)
        return control

    @classmethod
    async def respond_with_coop(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        view_state.set_player_count(ButtonInfoOptions.coop)
        return ButtonInfoMenu.button_info_control(view_state)

    @classmethod
    async def respond_with_solo(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        view_state.set_player_count(ButtonInfoOptions.solo)
        return ButtonInfoMenu.button_info_control(view_state)

    @classmethod
    async def respond_with_desktop(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        view_state.set_device(ButtonInfoOptions.desktop)
        return ButtonInfoMenu.button_info_control(view_state)

    @classmethod
    async def respond_with_mobile(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        view_state.set_device(ButtonInfoOptions.mobile)
        return ButtonInfoMenu.button_info_control(view_state)

    @classmethod
    async def respond_with_limit_break(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        view_state.set_max_level(ButtonInfoOptions.limit_break)
        return ButtonInfoMenu.button_info_control(view_state)

    @classmethod
    async def respond_with_super_limit_break(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        view_state.set_max_level(ButtonInfoOptions.super_limit_break)
        return ButtonInfoMenu.button_info_control(view_state)

    @staticmethod
    def button_info_control(state: ButtonInfoViewState):
        if state is None:
            return None
        reaction_list = ButtonInfoMenuPanes.get_user_reaction_list(state.display_options)
        return EmbedWrapper(
            ButtonInfoView.embed(state),
            reaction_list
        )


class ButtonInfoMenuPanes(MenuPanes):
    INITIAL_EMOJI = ButtonInfoEmoji.home

    DATA = {
        ButtonInfoEmoji.left: (ButtonInfoMenu.respond_with_left, None),
        ButtonInfoEmoji.right: (ButtonInfoMenu.respond_with_right, None),
        ButtonInfoEmoji.home: (ButtonInfoMenu.respond_with_button_info, ButtonInfoView.VIEW_TYPE),
        ButtonInfoEmoji.coop: (ButtonInfoMenu.respond_with_coop, ButtonInfoView.VIEW_TYPE),
        ButtonInfoEmoji.solo: (ButtonInfoMenu.respond_with_solo, ButtonInfoView.VIEW_TYPE),
        ButtonInfoEmoji.desktop: (ButtonInfoMenu.respond_with_desktop, ButtonInfoView.VIEW_TYPE),
        ButtonInfoEmoji.mobile: (ButtonInfoMenu.respond_with_mobile, ButtonInfoView.VIEW_TYPE),
        ButtonInfoEmoji.limit_break: (ButtonInfoMenu.respond_with_limit_break, ButtonInfoView.VIEW_TYPE),
        ButtonInfoEmoji.super_limit_break: (ButtonInfoMenu.respond_with_super_limit_break, ButtonInfoView.VIEW_TYPE),
    }

    HIDDEN_EMOJIS = [
        ButtonInfoEmoji.home,
    ]

    OPTIONAL_EMOJIS = [
        ButtonInfoEmoji.coop,
        ButtonInfoEmoji.solo,
        ButtonInfoEmoji.desktop,
        ButtonInfoEmoji.mobile,
        ButtonInfoEmoji.limit_break,
        ButtonInfoEmoji.super_limit_break,
    ]

    @classmethod
    def get_user_reaction_list(cls, current_options: ButtonInfoToggles):
        other_toggle_reactions = []
        if current_options.players == ButtonInfoOptions.coop:
            other_toggle_reactions.append(ButtonInfoEmoji.solo)
        elif current_options.players == ButtonInfoOptions.solo:
            other_toggle_reactions.append(ButtonInfoEmoji.coop)

        if current_options.device == ButtonInfoOptions.desktop:
            other_toggle_reactions.append(ButtonInfoEmoji.mobile)
        elif current_options.device == ButtonInfoOptions.mobile:
            other_toggle_reactions.append(ButtonInfoEmoji.desktop)

        if current_options.max_level == ButtonInfoOptions.limit_break:
            other_toggle_reactions.append(ButtonInfoEmoji.super_limit_break)
        elif current_options.max_level == ButtonInfoOptions.super_limit_break:
            other_toggle_reactions.append(ButtonInfoEmoji.limit_break)

        return [_ for _ in cls.emoji_names() if _ not in cls.OPTIONAL_EMOJIS] + other_toggle_reactions
