from typing import Optional

from discord import Message
from discordmenu.embed.menu import EmbedControl, EmbedMenu
from tsutils.menu.components.panes import MenuPanes, emoji_buttons

from padinfo.view.id import IdView, IdViewState
from padinfo.view.leader_skill_single import LeaderSkillSingleView, LeaderSkillSingleViewState


class LeaderSkillSingleMenu:
    MENU_TYPE = 'LeaderSkillSingle'

    @staticmethod
    def menu():
        return EmbedMenu(LeaderSkillSingleMenuPanes.transitions(),
                         LeaderSkillSingleMenu.ls_control)

    @staticmethod
    async def respond_with_ls(message: Optional[Message], ims, *, dbcog, user_config, **data):
        ls_view_state = await LeaderSkillSingleViewState.deserialize(dbcog, user_config, ims)
        ls_control = LeaderSkillSingleMenu.ls_control(ls_view_state)
        return ls_control

    @staticmethod
    async def respond_with_id(message: Optional[Message], ims, *, dbcog, user_config, **data):
        id_view_state = await IdViewState.deserialize(dbcog, user_config, ims)
        id_control = LeaderSkillSingleMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    def ls_control(state: LeaderSkillSingleViewState):
        return EmbedControl(
            [LeaderSkillSingleView.embed(state)],
            LeaderSkillSingleMenuPanes.emoji_names()
        )

    @staticmethod
    def id_control(state: IdViewState):
        return EmbedControl(
            [IdView.embed(state)],
            LeaderSkillSingleMenuPanes.emoji_names()
        )


class LeaderSkillSingleEmoji:
    home = emoji_buttons["home"]
    id = '\N{SQUARED ID}'


class LeaderSkillSingleMenuPanes(MenuPanes):
    INITIAL_EMOJI = LeaderSkillSingleEmoji.home
    DATA = {
        LeaderSkillSingleEmoji.home: (LeaderSkillSingleMenu.respond_with_ls, None),
        LeaderSkillSingleEmoji.id: (LeaderSkillSingleMenu.respond_with_id, IdView.VIEW_TYPE),
    }
