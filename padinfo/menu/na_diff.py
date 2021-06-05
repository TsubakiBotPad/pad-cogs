from typing import Optional

from discord import Message
from discordmenu.embed.control import EmbedControl
from discordmenu.embed.menu import EmbedMenu
from discordmenu.emoji.emoji_cache import emoji_cache
from tsutils.enums import Server, ChildMenuSelector
from tsutils.menu.panes import MenuPanes

from padinfo.menu.simple_text import SimpleTextMenu
from padinfo.view.id import IdViewState, IdView
from padinfo.view.simple_text import SimpleTextViewState, SimpleTextView


class NaDiffEmoji:
    home = '\N{HOUSE BUILDING}'
    na = '\N{REGIONAL INDICATOR SYMBOL LETTER U}\N{REGIONAL INDICATOR SYMBOL LETTER S}'
    jp = '\N{REGIONAL INDICATOR SYMBOL LETTER J}\N{REGIONAL INDICATOR SYMBOL LETTER P}'


class NaDiffMenu:
    MENU_TYPE = ChildMenuSelector.NaDiffMenu.name

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = NaDiffMenu.id_control
        embed = EmbedMenu(NaDiffMenuPanes.transitions(), initial_control,
                          delete_func=NaDiffMenu.respond_with_delete)
        return embed

    @staticmethod
    async def respond_with_home(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        if view_state.set_na_diff_invalid_message(ims):
            new_view_state = await SimpleTextViewState.deserialize(dgcog, user_config, ims)
            return NaDiffMenu.message_control(new_view_state)
        return await NaDiffMenu.respond_with_na(message, ims, **data)

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
    async def respond_with_delete(message: Optional[Message], ims, **data):
        if not ims.get('is_child'):
            return await message.delete()
        if ims.get('idle_message'):
            ims['menu_type'] = SimpleTextMenu.MENU_TYPE
            ims['message'] = ims['idle_message']
            return await SimpleTextMenu.respond_with_message(message, ims, **data)
        return await message.edit(embed=None)

    @staticmethod
    def id_control(state: IdViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [IdView.embed(state)],
            reaction_list or [emoji_cache.get_by_name(e) for e in NaDiffMenuPanes.emoji_names()]
        )

    @staticmethod
    def message_control(state: SimpleTextViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [SimpleTextView.embed(state)],
            reaction_list
        )


class NaDiffMenuPanes(MenuPanes):
    DATA = {
        NaDiffEmoji.home: (NaDiffMenu.respond_with_home, IdView.VIEW_TYPE),
        NaDiffEmoji.na: (NaDiffMenu.respond_with_na, IdView.VIEW_TYPE),
        NaDiffEmoji.jp: (NaDiffMenu.respond_with_jp, IdView.VIEW_TYPE),
    }
    HIDDEN_EMOJIS = [
        NaDiffEmoji.home,
    ]
