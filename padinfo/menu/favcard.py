from typing import Optional

from discord import Message
from discordmenu.embed.emoji import DELETE_MESSAGE_EMOJI
from discordmenu.embed.menu import EmbedMenu
from discordmenu.embed.transitions import EmbedMenuDefaultTransitions, EmbedTransition
from discordmenu.embed.wrapper import EmbedWrapper
from tsutils.menu.components.panes import MenuPanes
from tsutils.menu.simple_text import SimpleTextMenu
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.menu.components.evo_scroll_mixin import EvoScrollMenu
from padinfo.view.favcard import FavcardViewState, FavcardView


class FavcardMenu(EvoScrollMenu):
    MENU_TYPE = "Favcard"
    VIEW_STATE_TYPE = FavcardViewState

    @staticmethod
    def get_panes_type():
        #  TODO: change this to a property & classmethod once we update to Python 3.9
        return FavcardMenuPanes

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = FavcardMenu.home_control

        embed = EmbedMenu(FavcardMenuPanes.transitions(), initial_control,
                          EmbedMenuDefaultTransitions(
                              delete_message=EmbedTransition(DELETE_MESSAGE_EMOJI, FavcardMenu.respond_with_delete)))
        return embed

    @classmethod
    async def respond_with_home(cls, _message: Optional[Message], ims, **data):
        dbcog = data["dbcog"]
        user_config = data['user_config']
        view_state = await FavcardViewState.deserialize(dbcog, user_config, ims)
        control = FavcardMenu.home_control(view_state)
        return control

    @staticmethod
    async def respond_with_delete(message: Optional[Message], ims, **data):
        ims['menu_type'] = SimpleTextMenu.MENU_TYPE
        ims['message'] = 'Operation cancelled'
        return await SimpleTextMenu.respond_with_message(message, ims, **data)

    @staticmethod
    async def respond_with_select(message: Optional[Message], ims, **data):
        dbcog = data["dbcog"]
        user_config = data['user_config']
        view_state = await FavcardViewState.deserialize(dbcog, user_config, ims)
        await view_state.set_favcard(dbcog, ims)
        new_card = MonsterHeader.text_with_emoji(dbcog.get_monster(int(ims["resolved_monster_id"])))
        ims['menu_type'] = SimpleTextMenu.MENU_TYPE
        ims['message'] = f"Your favcard has been set to {new_card}"
        return await SimpleTextMenu.respond_with_message(message, ims, **data)

    @staticmethod
    def home_control(state: FavcardViewState):
        if state is None:
            return None
        return EmbedWrapper(
            FavcardView.embed(state),
            FavcardMenuPanes.emoji_names()
        )


class FavcardMenuEmoji:
    left = '\N{BLACK LEFT-POINTING TRIANGLE}'
    right = '\N{BLACK RIGHT-POINTING TRIANGLE}'
    delete = '\N{CROSS MARK}'
    select = '\N{WHITE HEAVY CHECK MARK}'
    home = '\N{HOUSE BUILDING}'


class FavcardMenuPanes(MenuPanes):
    INITIAL_EMOJI = FavcardMenuEmoji.home

    DATA = {
        FavcardMenuEmoji.left: (FavcardMenu.respond_with_left, None),
        FavcardMenuEmoji.right: (FavcardMenu.respond_with_right, None),
        FavcardMenuEmoji.delete: (FavcardMenu.respond_with_delete, None),
        FavcardMenuEmoji.select: (FavcardMenu.respond_with_select, None),
        FavcardMenuEmoji.home: (FavcardMenu.respond_with_home, FavcardView.VIEW_TYPE),
    }
    HIDDEN_EMOJIS = [
        FavcardMenuEmoji.delete,
        FavcardMenuEmoji.home,
    ]
