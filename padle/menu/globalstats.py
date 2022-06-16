from discord import Message
from discordmenu.embed.menu import EmbedMenu
from discordmenu.embed.wrapper import EmbedWrapper
from padle.view.globalstats_view import GlobalStatsView, GlobalStatsViewState
from tsutils.menu.components.panes import MenuPanes
from typing import Optional


class ScrollEmojis:
    prev_page = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
    next_page = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'
    home = '\N{HOUSE BUILDING}'

class GlobalStatsMenu:
    MENU_TYPE = 'PADleGlobalStatsMenu'

    view_types = {
        GlobalStatsViewState.VIEW_STATE_TYPE: GlobalStatsView
    }

    @staticmethod
    def menu(initial_control=None):
        if initial_control is None:
            initial_control = GlobalStatsMenu.control
        embed = EmbedMenu(GlobalStatsMenuPanes.transitions(), initial_control)
        return embed

    @classmethod
    async def respond_with_left(cls, message: Optional[Message], ims, **data):
        GlobalStatsViewState.decrement_page(ims)
        state = await cls._get_view_state(ims, **data)
        return GlobalStatsMenu.control(state)

    @classmethod
    async def respond_with_right(cls, message: Optional[Message], ims, **data):
        GlobalStatsViewState.increment_page(ims)
        state = await cls._get_view_state(ims, **data)
        return GlobalStatsMenu.control(state)

    @classmethod
    async def _get_view_state(cls, ims: dict, **data) -> GlobalStatsViewState:
        dbcog = data['dbcog']
        user_config = data['user_config']
        padle_cog = data['padle_cog']
        return await GlobalStatsViewState.deserialize(dbcog, user_config, padle_cog, ims)

    @classmethod
    async def respond_with_pane(cls, message: Optional[Message], ims, **data) -> EmbedWrapper:
        view_state = await cls._get_view_state(ims, **data)
        return GlobalStatsMenu.control(view_state)

    @staticmethod
    def control(state: GlobalStatsViewState):
        if state is None:
            return None
        reaction_list = GlobalStatsMenuPanes.get_initial_reaction_list()
        return EmbedWrapper(
            GlobalStatsView.embed(state),
            reaction_list
        )


class GlobalStatsMenuPanes(MenuPanes):
    INITIAL_EMOJI = ScrollEmojis.home
    
    DATA = {
        ScrollEmojis.next_page: (GlobalStatsMenu.respond_with_right, GlobalStatsView.VIEW_TYPE),
        ScrollEmojis.prev_page: (GlobalStatsMenu.respond_with_left, GlobalStatsView.VIEW_TYPE),
        ScrollEmojis.home: (GlobalStatsMenu.respond_with_pane, GlobalStatsView.VIEW_TYPE),
    }
    
    HIDDEN_EMOJIS = [ScrollEmojis.home]

    @classmethod
    def get_initial_reaction_list(cls):
        return [ScrollEmojis.prev_page, ScrollEmojis.next_page]
