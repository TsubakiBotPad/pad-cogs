from typing import Optional

from discord import Message
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from tsutils import char_to_emoji
from tsutils.menu.panes import emoji_buttons, MenuPanes

from padinfo.view.button_info import ButtonInfoViewState, ButtonInfoView


class ButtonInfoEmoji:
    delete = '\N{CROSS MARK}'
    home = emoji_buttons['home']
    solo = '\N{STANDING PERSON}'
    coop = '\N{ADULT}\N{ZERO WIDTH JOINER}\N{HANDSHAKE}\N{ZERO WIDTH JOINER}\N{ADULT}'
    mobile = '\N{MOBILE PHONE}'
    pc = '\N{DESKTOP COMPUTER}'
    # temporary until I figure out the custom/fallback emoji stuff
    limit_break = char_to_emoji('1')
    super_limit_break = char_to_emoji('2')


class ButtonInfoMenu:
    MENU_TYPE = 'ButtonInfo'

    @staticmethod
    def menu():
        return EmbedMenu(ButtonInfoMenuPanes.transitions(), ButtonInfoMenu.button_info_control)

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

    @staticmethod
    def button_info_control(state: ButtonInfoViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [ButtonInfoView.embed(state)],
            reaction_list
        )


class ButtonInfoMenuPanes(MenuPanes):
    INITIAL_EMOJI = ButtonInfoEmoji.home

    DATA = {
        ButtonInfoEmoji.delete: (ButtonInfoMenu.respond_with_delete, None),
        ButtonInfoEmoji.home: (ButtonInfoMenu.respond_with_button_info, ButtonInfoView.VIEW_TYPE),
        # delete = '\N{CROSS MARK}'
        # home = emoji_buttons['home']
        # solo = '\N{STANDING PERSON}'
        # coop = '\N{ADULT}\N{ZERO WIDTH JOINER}\N{HANDSHAKE}\N{ZERO WIDTH JOINER}\N{ADULT}'
        # mobile = '\N{MOBILE PHONE}'
        # pc = '\N{DESKTOP COMPUTER}'
        # # temporary until I figure out the custom/fallback emoji stuff
        # limit_break = char_to_emoji('1')
        # super_limit_break = char_to_emoji('2')
    }
