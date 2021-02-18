from typing import TYPE_CHECKING, Optional

from discord import Message
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji.emoji_cache import emoji_cache

from padinfo.menu.common import MenuPanes, emoji_buttons
from padinfo.view.id import IdView, IdViewState
from padinfo.view.leader_skill_single import LeaderSkillSingleView, LeaderSkillSingleViewState

if TYPE_CHECKING:
    pass

menu_emoji_config = EmbedMenuEmojiConfig()


class LeaderSkillSingleMenu:
    MENU_TYPE = 'LeaderSkillSingle'

    @staticmethod
    def menu():
        return EmbedMenu(LeaderSkillSingleMenuPanes.transitions(),
                         LeaderSkillSingleMenu.ls_control, menu_emoji_config)

    @staticmethod
    async def respond_with_ls(message: Optional[Message], ims, *, dgcog, user_config, **data):
        ls_view_state = await LeaderSkillSingleViewState.deserialize(dgcog, user_config, ims)
        ls_control = LeaderSkillSingleMenu.ls_control(ls_view_state)
        return ls_control

    @staticmethod
    async def respond_with_id(message: Optional[Message], ims, *, dgcog, user_config, **data):
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = LeaderSkillSingleMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    def ls_control(state: LeaderSkillSingleViewState):
        return EmbedControl(
            [LeaderSkillSingleView.embed(state)],
            [emoji_cache.get_by_name(e) for e in LeaderSkillSingleMenuPanes.emoji_names()]
        )

    @staticmethod
    def id_control(state: IdViewState):
        return EmbedControl(
            [IdView.embed(state)],
            [emoji_cache.get_by_name(e) for e in LeaderSkillSingleMenuPanes.emoji_names()]
        )


class LeaderSkillSingleMenuPanes(MenuPanes):
    INITIAL_EMOJI = emoji_buttons['home']
    DATA = {
        LeaderSkillSingleMenu.respond_with_ls: (emoji_buttons['home'], None),
        LeaderSkillSingleMenu.respond_with_id: ('\N{SQUARED ID}', IdView.VIEW_TYPE),
    }
