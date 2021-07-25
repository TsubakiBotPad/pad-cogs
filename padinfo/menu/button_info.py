from typing import Optional

from discord import Message
from discordmenu.embed.control import EmbedControl
from discordmenu.embed.menu import EmbedMenu
from tsutils import char_to_emoji
from tsutils.menu.panes import emoji_buttons, MenuPanes

from padinfo.view.button_info import ButtonInfoOptions, ButtonInfoToggles, ButtonInfoViewState, ButtonInfoView


class ButtonInfoEmoji:
    delete = '\N{CROSS MARK}'
    home = emoji_buttons['home']
    coop = '\N{BUSTS IN SILHOUETTE}'
    solo = '\N{BUST IN SILHOUETTE}'
    desktop = '\N{DESKTOP COMPUTER}'
    mobile = '\N{MOBILE PHONE}'
    # temporary until I figure out the custom/fallback emoji stuff
    limit_break = char_to_emoji('1')
    super_limit_break = char_to_emoji('2')


class ButtonInfoMenu:
    MENU_TYPE = 'ButtonInfo'

    @staticmethod
    def menu():
        return EmbedMenu(ButtonInfoMenuPanes.transitions(), ButtonInfoMenu.button_info_control)

    @classmethod
    async def _get_view_state(cls, ims: dict, **data) -> ButtonInfoViewState:
        dgcog = data['dgcog']
        user_config = data['user_config']
        return await ButtonInfoViewState.deserialize(dgcog, user_config, ims)

    @staticmethod
    async def respond_with_delete(message: Message, ims, **data):
        return await message.delete()

    @staticmethod
    async def respond_with_button_info(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        view_state = await ButtonInfoViewState.deserialize(dgcog, user_config, ims)
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
        return EmbedControl(
            [ButtonInfoView.embed(state)],
            reaction_list
        )


class ButtonInfoMenuPanes(MenuPanes):
    INITIAL_EMOJI = ButtonInfoEmoji.home

    DATA = {
        ButtonInfoEmoji.delete: (ButtonInfoMenu.respond_with_delete, None),
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
