from typing import List, Optional, Type

from discord import Message
from discordmenu.embed.menu import EmbedControl, EmbedMenu
from tsutils.emoji import char_to_emoji
from tsutils.menu.components.panes import MenuPanes, emoji_buttons
from padle.view.padle_scroll_view import PADleScrollView, PADleScrollViewState


class ScrollEmojis:
    prev_page = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
    next_page = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'
    delete = '\N{CROSS MARK}'


class PADleScrollMenu:
    MENU_TYPE = 'PADleScrollMenu'
    
    view_types = {
        PADleScrollViewState.VIEW_STATE_TYPE: PADleScrollView
    }

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = PADleScrollMenu.control
        embed = EmbedMenu(PADleMenuPanes.transitions(), initial_control)
        return embed
    
    @classmethod
    async def respond_with_left(cls, message: Optional[Message], ims, **data):
        print("Left clicked!!")
        view_state = await cls._get_view_state(ims, **data)
        view_state.decrement_page()
        return PADleScrollMenu.control(view_state)

    @classmethod
    async def respond_with_right(cls, message: Optional[Message], ims, **data):
        view_state = await cls._get_view_state(ims, **data)
        view_state.increment_page()
        return PADleScrollMenu.control(view_state)
    
    @classmethod
    def control(cls, state: PADleScrollViewState):
        if state is None:
            return None
        reaction_list = state.reaction_list
        view_type = cls._get_view(state)
        return EmbedControl(
            [view_type.embed(state)],
            reaction_list
        )
    
    @classmethod
    def _get_view(cls, state: PADleScrollViewState) -> Type[PADleScrollView]:
        return cls.view_types.get(state.VIEW_STATE_TYPE) or PADleScrollView
    
    @classmethod
    async def _get_view_state(cls, ims: dict, **data) -> PADleScrollViewState:
        return PADleScrollViewState()
        

class PADleMenuPanes(MenuPanes):
    DATA = {
        ScrollEmojis.next_page: (PADleScrollMenu.respond_with_right, PADleScrollView.VIEW_TYPE, None),
        ScrollEmojis.prev_page: (PADleScrollMenu.respond_with_left, PADleScrollView.VIEW_TYPE, None),
    }
    HIDDEN_EMOJIS = [ScrollEmojis.delete]
    
    @classmethod
    def get_initial_reaction_list(cls):
        return [ScrollEmojis.prev_page, ScrollEmojis.next_page]