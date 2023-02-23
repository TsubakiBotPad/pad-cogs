from typing import Optional

from discord import Message
from discordmenu.embed.menu import EmbedMenu
from discordmenu.embed.wrapper import EmbedWrapper
from tsutils.emoji import char_to_emoji
from tsutils.menu.components.panes import MenuPanes, emoji_buttons

from padinfo.view.id import IdView, IdViewState
from padinfo.view.leader_skill import LeaderSkillView, LeaderSkillViewState


class LeaderSkillMenu:
    MENU_TYPE = 'LeaderSkill'

    @staticmethod
    def menu():
        return EmbedMenu(LeaderSkillMenuPanes.transitions(), LeaderSkillMenu.ls_control)

    @staticmethod
    async def respond_with_right(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']
        # Extract the query from the ls state
        ims['query'] = ims['r_query']
        ims['qs'] = ims['rqs']
        ims['resolved_monster_id'] = None
        id_view_state = await IdViewState.deserialize(dbcog, user_config, ims)
        id_control = LeaderSkillMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_with_left(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']

        # Extract the query from the ls state
        ims['query'] = ims['l_query']
        ims['qs'] = ims['lqs']
        ims['resolved_monster_id'] = None
        id_view_state = await IdViewState.deserialize(dbcog, user_config, ims)
        id_control = LeaderSkillMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_with_house(message: Optional[Message], ims, **data):
        dbcog = data['dbcog']
        user_config = data['user_config']
        ls_view_state = await LeaderSkillViewState.deserialize(dbcog, user_config, ims)
        ls_control = LeaderSkillMenu.ls_control(ls_view_state)
        return ls_control

    @staticmethod
    def ls_control(state: LeaderSkillViewState):
        return EmbedWrapper(
            LeaderSkillView.embed(state),
            LeaderSkillMenuPanes.emoji_names()
        )

    @staticmethod
    def id_control(state: IdViewState):
        return EmbedWrapper(
            IdView.embed(state),
            LeaderSkillMenuPanes.emoji_names()
        )


class LeaderSkillEmoji:
    home = emoji_buttons['home']
    left = char_to_emoji('l')
    right = char_to_emoji('r')


class LeaderSkillMenuPanes(MenuPanes):
    INITIAL_EMOJI = LeaderSkillEmoji.home
    DATA = {
        LeaderSkillEmoji.home: (LeaderSkillMenu.respond_with_house, None),
        LeaderSkillEmoji.left: (LeaderSkillMenu.respond_with_left, IdView.VIEW_TYPE),
        LeaderSkillEmoji.right: (LeaderSkillMenu.respond_with_right, IdView.VIEW_TYPE),
    }
