from typing import Optional

from discord import Message
from discordmenu.embed.control import EmbedControl
from discordmenu.embed.menu import EmbedMenu
from discordmenu.emoji.emoji_cache import emoji_cache
from tsutils import char_to_emoji
from tsutils.enums import Server
from tsutils.menu.panes import MenuPanes

from padinfo.view.id import IdViewState, IdView


class NaDiffEmoji:
    na = '\N{REGIONAL INDICATOR SYMBOL LETTER U}\N{REGIONAL INDICATOR SYMBOL LETTER S}'
    jp = '\N{REGIONAL INDICATOR SYMBOL LETTER J}\N{REGIONAL INDICATOR SYMBOL LETTER P}'


class NaDiffMenu:
    MENU_TYPE = "NaDiffMenu"

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = NaDiffMenu.id_control
        embed = EmbedMenu(NaDiffMenuPanes.transitions(), initial_control)
        return embed

    @staticmethod
    async def respond_with_na(message: Optional[Message], ims, **data):
        return await NaDiffMenu.respond_with_id(message, ims, Server.NA, **data)

    @staticmethod
    async def respond_with_jp(message: Optional[Message], ims, **data):
        return await NaDiffMenu.respond_with_id(message, ims, Server.COMBINED, **data)

    @staticmethod
    async def respond_with_id(message: Optional[Message], ims, server: Server, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        await view_state.set_server(dgcog, server)
        control = NaDiffMenu.id_control(view_state)
        return control

    @staticmethod
    def id_control(state: IdViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [IdView.embed(state)],
            reaction_list or [emoji_cache.get_by_name(e) for e in NaDiffMenuPanes.emoji_names()]
        )


class NaDiffMenuPanes(MenuPanes):
    DATA = {
        NaDiffEmoji.na: (NaDiffMenu.respond_with_na, IdView.VIEW_TYPE),
        NaDiffEmoji.jp: (NaDiffMenu.respond_with_jp, IdView.VIEW_TYPE),
    }
