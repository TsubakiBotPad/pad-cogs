from typing import Optional

from discord import Message
from discordmenu.embed.control import EmbedControl
from discordmenu.embed.menu import EmbedMenu
from tsutils.menu.panes import MenuPanes, emoji_buttons

from dungeoncog.view.simple import SimpleViewState, SimpleView


class SimpleNames:
    home = 'home'


class SimpleMenu:
    MENU_TYPE = 'SimpleMenu'
    message = None

    @staticmethod
    def menu():
        embed = EmbedMenu(SimpleMenuPanes.transitions(), SimpleMenu.message_control,
                          delete_func=SimpleMenu.respond_with_delete)
        return embed

    @staticmethod
    async def respond_with_message(message: Optional[Message], ims, **data):
        dgcog = data.get('dgcog')
        color = data.get('color')
        view_state = await SimpleViewState.deserialize(dgcog, color, ims, 0)
        control = SimpleMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_delete(message: Optional[Message], ims, **data):
        return await message.delete()

    @staticmethod
    async def respond_with_right(message: Optional[Message], ims, **data):
        dgcog = data.get('dgcog')
        color = data.get('color')
        view_state = await SimpleViewState.deserialize(dgcog, color, ims, 1)
        control = SimpleMenu.message_control(view_state)
        return control

    @staticmethod
    def message_control(state: SimpleViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [SimpleView.embed(state)],
            reaction_list
        )


class SimpleEmoji:
    home = emoji_buttons['home']
    right = '\N{BLACK RIGHT-POINTING TRIANGLE}'


class SimpleMenuPanes(MenuPanes):
    INITIAL_EMOJI = SimpleEmoji.home
    DATA = {
        SimpleEmoji.home: (SimpleMenu.respond_with_message, SimpleNames.home),
        SimpleEmoji.right: (SimpleMenu.respond_with_right, SimpleView.VIEW_TYPE)

    }
    HIDDEN_EMOJIS = [
        SimpleNames.home,
    ]
