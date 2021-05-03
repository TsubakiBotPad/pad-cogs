from typing import Optional

from discord import Message
from discordmenu.embed.control import EmbedControl
from discordmenu.embed.menu import EmbedMenu

from dungeon.view.dungeon import DungeonViewState, DungeonView
from padinfo.menu.common import MenuPanes, emoji_buttons


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
        dgcog = data.get('dgcog')
        user_config = data.get('user_config')
        view_state = await DungeonViewState.deserialize(dgcog, user_config, ims)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_delete(message: Optional[Message], ims, **data):
        return await message.delete()

    @staticmethod
    async def respond_with_previous_monster(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        view_state = await DungeonViewState.deserialize(dgcog, user_config, ims, 0, -1)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_next_monster(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        view_state = await DungeonViewState.deserialize(dgcog, user_config, ims, 0, 1)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_previous_floor(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        view_state = await DungeonViewState.deserialize(dgcog, user_config, ims, -1, 0)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    async def respond_with_next_floor(message: Optional[Message], ims, **data):
        print('next floor')
        dgcog = data['dgcog']
        user_config = data['user_config']
        view_state = await DungeonViewState.deserialize(dgcog, user_config, ims, 1, 0)
        control = DungeonMenu.message_control(view_state)
        return control

    @staticmethod
    def message_control(state: DungeonViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [DungeonView.embed(state)],
            reaction_list
        )





class DungeonEmoji:
    home = emoji_buttons['home']
    previous_monster_emoji = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
    next_monster_emoji = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'
    next_floor = '\N{UPWARDS BLACK ARROW}'
    previous_floor = '\N{DOWNWARDS BLACK ARROW}'
    next_page = '📖'


class DungeonMenuPanes(MenuPanes):
    INITIAL_EMOJI = DungeonEmoji.home
    DATA = {
        DungeonEmoji.home: (DungeonMenu.respond_with_message, DungeonView.VIEW_TYPE),
        DungeonEmoji.previous_monster_emoji: (DungeonMenu.respond_with_previous_monster, DungeonView.VIEW_TYPE),
        DungeonEmoji.next_monster_emoji: (DungeonMenu.respond_with_next_monster, DungeonView.VIEW_TYPE),
        DungeonEmoji.previous_floor: (DungeonMenu.respond_with_previous_floor, DungeonView.VIEW_TYPE),
        DungeonEmoji.next_floor: (DungeonMenu.respond_with_next_floor, DungeonView.VIEW_TYPE)

    }
    HIDDEN_EMOJIS = [

    ]
