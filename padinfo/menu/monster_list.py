from typing import Optional

from discord import Message
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from tsutils import char_to_emoji

from padinfo.menu.common import emoji_buttons, MenuPanes
from padinfo.menu.id import IdMenu, IdMenuPanes
from padinfo.view.id import IdView
from padinfo.view.monster_list import MonsterListView, MonsterListViewState

menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')


class MonsterListPaneNames:
    home = 'home'
    refresh = 'refresh'
    reset = 'reset'


class MonsterListMenu:
    MENU_TYPE = 'MonsterListMenu'
    CHILD_MENU_TYPE = 'IdMenu'

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = MonsterListMenu.monster_list_control
        embed = EmbedMenu(MonsterListMenuPanes.transitions(), initial_control, menu_emoji_config)
        return embed

    @staticmethod
    async def respond_with_refresh(message: Optional[Message], ims, **data):
        # this is only called once on message load
        if data.get('child_message_id'):
            ims['child_message_id'] = data['child_message_id']
        return await MonsterListMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_reset(message: Optional[Message], ims, **data):
        # replace with the overview list after the child menu changes
        return await MonsterListMenu.respond_with_monster_list(message, ims, **data)

    @staticmethod
    async def respond_with_monster_list(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        view_state = await MonsterListViewState.deserialize(dgcog, user_config, ims)
        control = MonsterListMenu.monster_list_control(view_state)
        return control

    @staticmethod
    async def respond_with_n(message: Optional[Message], ims, n, **data):
        ims['resolved_monster_id'] = int(ims['monster_list'][n])
        reaction_list = IdMenuPanes.emoji_names()
        if not data.get('child_message_ims') or data['child_message_ims']['menu_type'] != IdMenu.MENU_TYPE:
            # default to the overview screen if we weren't already on a screen
            ims['reaction_list'] = reaction_list
            ims['is_child'] = True
            return await IdMenu.respond_with_current_id(message, ims, **data)
        data['child_message_ims']['reaction_list'] = reaction_list
        data['child_message_ims']['resolved_monster_id'] = int(ims['resolved_monster_id'])
        return await IdMenu.respond_with_refresh(message, data['child_message_ims'], **data)

    @staticmethod
    async def respond_with_0(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 0, **data)

    @staticmethod
    async def respond_with_1(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 1, **data)

    @staticmethod
    async def respond_with_2(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 2, **data)

    @staticmethod
    async def respond_with_3(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 3, **data)

    @staticmethod
    async def respond_with_4(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 4, **data)

    @staticmethod
    async def respond_with_5(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 5, **data)

    @staticmethod
    async def respond_with_6(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 6, **data)

    @staticmethod
    async def respond_with_7(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 7, **data)

    @staticmethod
    async def respond_with_8(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 8, **data)

    @staticmethod
    async def respond_with_9(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 9, **data)

    @staticmethod
    async def respond_with_10(message: Optional[Message], ims, **data):
        return await MonsterListMenu.respond_with_n(message, ims, 10, **data)

    @staticmethod
    def monster_list_control(state: MonsterListViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        return EmbedControl(
            [MonsterListView.embed(state)],
            reaction_list
        )

    @staticmethod
    def get_child_data(ims, emoji_clicked):
        pass


class MonsterListMenuPanes(MenuPanes):
    INITIAL_EMOJI = '\N{HOUSE BUILDING}'
    DATA = {
        MonsterListMenu.respond_with_monster_list: (emoji_buttons[MonsterListPaneNames.home], MonsterListPaneNames.home),
        MonsterListMenu.respond_with_0: (char_to_emoji('0'), IdView.VIEW_TYPE),
        MonsterListMenu.respond_with_1: (char_to_emoji('1'), IdView.VIEW_TYPE),
        MonsterListMenu.respond_with_2: (char_to_emoji('2'), IdView.VIEW_TYPE),
        MonsterListMenu.respond_with_3: (char_to_emoji('3'), IdView.VIEW_TYPE),
        MonsterListMenu.respond_with_4: (char_to_emoji('4'), IdView.VIEW_TYPE),
        MonsterListMenu.respond_with_5: (char_to_emoji('5'), IdView.VIEW_TYPE),
        MonsterListMenu.respond_with_6: (char_to_emoji('6'), IdView.VIEW_TYPE),
        MonsterListMenu.respond_with_7: (char_to_emoji('7'), IdView.VIEW_TYPE),
        MonsterListMenu.respond_with_8: (char_to_emoji('8'), IdView.VIEW_TYPE),
        MonsterListMenu.respond_with_9: (char_to_emoji('9'), IdView.VIEW_TYPE),
        MonsterListMenu.respond_with_10: ('\N{KEYCAP TEN}', IdView.VIEW_TYPE),
        MonsterListMenu.respond_with_refresh: (
            '\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}', MonsterListPaneNames.refresh),
        MonsterListMenu.respond_with_reset: (emoji_buttons['reset'], MonsterListPaneNames.reset)
    }
    HIDDEN_EMOJIS = [
        MonsterListPaneNames.home,
        MonsterListPaneNames.refresh,
        MonsterListPaneNames.reset,
    ]
