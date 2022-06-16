from math import ceil
from typing import Optional

from discord import Message
from discordmenu.embed.menu import EmbedMenu
from discordmenu.embed.wrapper import EmbedWrapper
from tsutils.menu.components.panes import MenuPanes

from padle.view.padle_scroll_view import PADleScrollView, PADleScrollViewState


class ScrollEmojis:
    prev_page = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
    next_page = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'


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
    def get_num_pages_ims(cls, ims):
        return ims['num_pages']

    @classmethod
    async def respond_with_left(cls, message: Optional[Message], ims, **data):
        if ims['current_page'] < PADleScrollMenu.get_num_pages_ims(ims) - 1:
            ims['current_page'] = ims['current_page'] + 1
        else:
            ims['current_page'] = 0
        return await PADleScrollMenu.respond_with_pane(message, ims, **data)

    @classmethod
    async def respond_with_right(cls, message: Optional[Message], ims, **data):
        if ims['current_page'] > 0:
            ims['current_page'] = ims['current_page'] - 1
        else:
            ims['current_page'] = PADleScrollMenu.get_num_pages_ims(ims) - 1
        return await PADleScrollMenu.respond_with_pane(message, ims, **data)

    @classmethod
    async def respond_with_pane(cls, message: Optional[Message], ims, **data) -> EmbedWrapper:
        dbcog = data['dbcog']
        user_config = data['user_config']
        padle_cog = data['padle_cog']
        view_state = await PADleScrollViewState.deserialize(dbcog, padle_cog, user_config, ims)
        return PADleScrollMenu.control(view_state)

    @staticmethod
    def control(state: PADleScrollViewState):
        if state is None:
            return None
        reaction_list = PADleMenuPanes.get_initial_reaction_list()
        return EmbedWrapper(
            PADleScrollView.embed(state),
            reaction_list
        )


class PADleMenuPanes(MenuPanes):
    INITIAL_EMOJI = ScrollEmojis.prev_page
    DATA = {
        ScrollEmojis.next_page: (PADleScrollMenu.respond_with_left, PADleScrollView.VIEW_TYPE),
        ScrollEmojis.prev_page: (PADleScrollMenu.respond_with_right, PADleScrollView.VIEW_TYPE),
    }

    @classmethod
    def get_initial_reaction_list(cls):
        return [ScrollEmojis.prev_page, ScrollEmojis.next_page]
