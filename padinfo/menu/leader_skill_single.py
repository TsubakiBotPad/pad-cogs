from typing import TYPE_CHECKING, Optional

from discord import Message
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji.emoji_cache import emoji_cache

from padinfo.view.id import IdView, IdViewState
from padinfo.view.leader_skill_single import LeaderSkillSingleView, LeaderSkillSingleViewState

if TYPE_CHECKING:
    pass

menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')


class LeaderSkillSingleMenu:
    EMOJI_BUTTON_NAMES = ('\N{HOUSE BUILDING}', '\N{SQUARED ID}', '\N{CROSS MARK}')
    MENU_TYPE = 'LeaderSkillSingle'

    @staticmethod
    def menu():
        transitions = {
            LeaderSkillSingleMenu.EMOJI_BUTTON_NAMES[0]: LeaderSkillSingleMenu.respond_to_house,
            LeaderSkillSingleMenu.EMOJI_BUTTON_NAMES[1]: LeaderSkillSingleMenu.view_ls,
        }
        return EmbedMenu(transitions, LeaderSkillSingleMenu.ls_control, menu_emoji_config)

    @staticmethod
    async def view_ls(message: Optional[Message], ims, *, dgcog, user_config, **data):
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = LeaderSkillSingleMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_to_house(message: Optional[Message], ims, *, dgcog, user_config, **data):
        ls_view_state = await LeaderSkillSingleViewState.deserialize(dgcog, user_config, ims)
        ls_control = LeaderSkillSingleMenu.ls_control(ls_view_state)
        return ls_control

    @staticmethod
    def ls_control(state: LeaderSkillSingleViewState):
        return EmbedControl(
            [LeaderSkillSingleView.embed(state)],
            [emoji_cache.get_by_name(e) for e in LeaderSkillSingleMenu.EMOJI_BUTTON_NAMES]
        )

    @staticmethod
    def id_control(state: IdViewState):
        return EmbedControl(
            [IdView.embed(state)],
            [emoji_cache.get_by_name(e) for e in LeaderSkillSingleMenu.EMOJI_BUTTON_NAMES]
        )
