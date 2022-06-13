from typing import Optional

from discord import Message
from discordmenu.embed.wrapper import EmbedWrapper
from discordmenu.embed.menu import EmbedMenu
from tsutils.menu.components.panes import MenuPanes, emoji_buttons

from dungeoncog.view.dungeon import DungeonViewState, DungeonView


class DungeonNames:
    home = 'home'


class DungeonMenu:
    MENU_TYPE = 'DungeonMenu'
    message = None

    @staticmethod
    def menu():
        embed = EmbedMenu(DungeonMenuPanes.transitions(), DungeonMenu.message_control,
                          delete_func=DungeonMenu.respond_with_delete)
        return embed

    @staticmethod
    async def respond_with_message(message: Optional[Message], ims, **data):
        dbcog = data.get('dbcog')
        view_state = await DungeonViewState.deserialize(dbcog, ims)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_verbose(message: Optional[Message], ims, **data):
        dbcog = data.get('dbcog')
        view_state = await DungeonViewState.deserialize(dbcog, ims, verbose_toggle=True)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_delete(message: Optional[Message], ims, **data):
        return await message.delete()

    @staticmethod
    async def respond_with_previous_monster(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        view_state = await DungeonViewState.deserialize(dbcog, ims, 0, -1)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_next_monster(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        view_state = await DungeonViewState.deserialize(dbcog, ims, 0, 1)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_previous_floor(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        view_state = await DungeonViewState.deserialize(dbcog, ims, -1, 0, reset_spawn=True)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_next_floor(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        view_state = await DungeonViewState.deserialize(dbcog, ims, 1, 0, reset_spawn=True)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_next_page(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        page = ims.get('page')
        if page == 0:
            page = 1
        else:
            page = 0
        view_state = await DungeonViewState.deserialize(dbcog, ims, page=page)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    def message_control(state: DungeonViewState):
        if state is None:
            return None
        return EmbedWrapper(
            DungeonView.embed(state),
            DungeonMenuPanes.emoji_names()
        )


class DungeonEmoji:
    home = emoji_buttons['home']
    verbose = '\N{SCROLL}'
    previous_monster = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
    next_monster = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'
    previous_floor = ('minus', '\N{DOWNWARDS BLACK ARROW}')
    next_floor = ('plus', '\N{UPWARDS BLACK ARROW}')
    next_page = '\N{OPEN BOOK}'


class DungeonMenuPanes(MenuPanes):
    INITIAL_EMOJI = DungeonEmoji.home

    DATA = {
        DungeonEmoji.home: (DungeonMenu.respond_with_message, DungeonView.VIEW_TYPE),
        DungeonEmoji.verbose: (DungeonMenu.respond_with_verbose, DungeonView.VIEW_TYPE),
        DungeonEmoji.previous_monster: (DungeonMenu.respond_with_previous_monster, DungeonView.VIEW_TYPE),
        DungeonEmoji.next_monster: (DungeonMenu.respond_with_next_monster, DungeonView.VIEW_TYPE),
        DungeonEmoji.previous_floor: (DungeonMenu.respond_with_previous_floor, DungeonView.VIEW_TYPE),
        DungeonEmoji.next_floor: (DungeonMenu.respond_with_next_floor, DungeonView.VIEW_TYPE),
        DungeonEmoji.next_page: (DungeonMenu.respond_with_next_page, DungeonView.VIEW_TYPE)
    }

    HIDDEN_EMOJIS = [
        DungeonEmoji.home
    ]
