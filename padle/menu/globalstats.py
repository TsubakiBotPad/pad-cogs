from discord import Message
from discordmenu.embed.menu import EmbedMenu
from discordmenu.embed.wrapper import EmbedWrapper
from padle.view.globalstats_view import GlobalStatsView, GlobalStatsViewState
from tsutils.menu.components.panes import MenuPanes
from typing import Optional


class ScrollEmojis:
    prev_page = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
    next_page = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'


class GlobalStatsMenu:
    MENU_TYPE = 'GlobalStatsMenu'

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
        if ims['current_day'] < ims['num_days']:
            ims['current_day'] = ims['current_day'] + 1
        else:
            ims['current_day'] = 1
        return await GlobalStatsMenu.respond_with_pane(message, ims, **data)

    @classmethod
    async def respond_with_right(cls, message: Optional[Message], ims, **data):
        if ims['current_day'] > 1:
            ims['current_day'] = ims['current_day'] - 1
        else:
            ims['current_day'] = ims['num_days']
        return await GlobalStatsMenu.respond_with_pane(message, ims, **data)

    @classmethod
    async def respond_with_pane(cls, message: Optional[Message], ims, **data) -> EmbedWrapper:
        dbcog = data['dbcog']
        user_config = data['user_config']
        daily_scores_list = data['daily_scores_list']
        cur_day_scores = data['cur_day_scores']
        view_state = await GlobalStatsViewState.deserialize(dbcog, user_config, daily_scores_list, cur_day_scores, ims)
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
    INITIAL_EMOJI = ScrollEmojis.prev_page
    DATA = {
        ScrollEmojis.next_page: (GlobalStatsMenu.respond_with_left, GlobalStatsView.VIEW_TYPE),
        ScrollEmojis.prev_page: (GlobalStatsMenu.respond_with_right, GlobalStatsView.VIEW_TYPE),
    }

    @classmethod
    def get_initial_reaction_list(cls):
        return [ScrollEmojis.prev_page, ScrollEmojis.next_page]
