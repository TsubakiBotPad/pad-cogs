from typing import Optional

from discord import Message
from discordmenu.embed.control import EmbedControl
from discordmenu.embed.menu import EmbedMenu

from tsutils.menu.panes import MenuPanes, emoji_buttons
from padinfo.view.simple_text import SimpleTextView, SimpleTextViewState


class SimpleTextNames:
    home = 'home'


class SimpleTextMenu:
    MENU_TYPE = 'SimpleTextMenu'
    message = None

    @staticmethod
    def menu():
        embed = EmbedMenu(SimpleTextMenuPanes.transitions(), SimpleTextMenu.message_control,
                          delete_func=SimpleTextMenu.respond_with_delete)
        return embed

    @staticmethod
    async def respond_with_message(message: Optional[Message], ims, **data):
        dgcog = data.get('dgcog')
        user_config = data.get('user_config')
        view_state = await SimpleTextViewState.deserialize(dgcog, user_config, ims)
        control = SimpleTextMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_delete(message: Optional[Message], ims, **data):
        return await message.delete()

    @staticmethod
    def message_control(state: SimpleTextViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [SimpleTextView.embed(state)],
            reaction_list
        )


class SimpleTextEmoji:
    home = emoji_buttons['home']


class SimpleTextMenuPanes(MenuPanes):
    INITIAL_EMOJI = SimpleTextEmoji.home
    DATA = {
        SimpleTextEmoji.home: (SimpleTextMenu.respond_with_message, SimpleTextNames.home),

    }
    HIDDEN_EMOJIS = [
        SimpleTextNames.home,
    ]
