from typing import Optional

from discord import Message
from discordmenu.embed.control import EmbedControl
from discordmenu.embed.menu import EmbedMenu

from dungeon.view.simple import SimpleViewState, SimpleView
from padinfo.menu.common import MenuPanes, emoji_buttons


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
        user_config = data.get('user_config')
        view_state = await SimpleViewState.deserialize(dgcog, user_config, ims)
        control = SimpleMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_delete(message: Optional[Message], ims, **data):
        return await message.delete()

    @staticmethod
    async def respond_with_right(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        print("test")
        view_state = await SimpleViewState.deserialize(dgcog, user_config, ims, 1)
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
