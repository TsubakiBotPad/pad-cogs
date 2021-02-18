from typing import TYPE_CHECKING, Optional

from discord import Message
from discordmenu.embed.control import EmbedControl
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu

from padinfo.view.simple_text import SimpleTextView
from padinfo.view_state.simple_text import SimpleTextViewState

if TYPE_CHECKING:
    pass

menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')


class SimpleTextNames:
    home = 'home'


class SimpleTextMenu:
    MENU_TYPE = 'SimpleTextMenu'
    message = None

    @staticmethod
    def menu():
        embed = EmbedMenu(SimpleTextMenuPanes.transitions(), SimpleTextMenu.message_control,
                          menu_emoji_config,
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


class SimpleTextMenuPanes:
    INITIAL_EMOJI = '\N{HOUSE BUILDING}'
    DATA = {
        SimpleTextMenu.respond_with_message: ('\N{HOUSE BUILDING}', SimpleTextNames.home),

    }
    HIDDEN_EMOJIS = [
        SimpleTextNames.home,
    ]

    @classmethod
    def emoji_names(cls):
        return [v[0] for k, v in cls.DATA.items() if v[1] not in cls.HIDDEN_EMOJIS]

    @classmethod
    def transitions(cls):
        return {v[0]: k for k, v in cls.DATA.items()}

    @classmethod
    def pane_types(cls):
        return {v[1]: k for k, v in cls.DATA.items() if v[1] and v[1] not in cls.HIDDEN_EMOJIS}

    @staticmethod
    def get_initial_reaction_list(number_of_evos: int):
        return SimpleTextMenuPanes.emoji_names()[:number_of_evos]

    @staticmethod
    def emoji_name_to_emoji(name: str):
        for _, data_pair in SimpleTextMenuPanes.DATA.items():
            if data_pair[1] == name:
                return data_pair[0]
        return None

    @staticmethod
    def emoji_name_to_function(name: str):
        for _, data_pair in SimpleTextMenuPanes.DATA.items():
            if data_pair[1] == name:
                return data_pair[1]
        return None
