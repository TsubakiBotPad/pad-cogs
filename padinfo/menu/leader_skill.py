from typing import TYPE_CHECKING, Optional

from discord import Message
from discordmenu.embed.emoji import EmbedMenuEmojiConfig
from discordmenu.embed.menu import EmbedMenu, EmbedControl
from discordmenu.emoji.emoji_cache import emoji_cache
from tsutils import char_to_emoji

from padinfo.view.id import IdView
from padinfo.view.leader_skill import LeaderSkillView
from padinfo.view_state.id import IdViewState
from padinfo.view_state.leader_skill import LeaderSkillViewState

if TYPE_CHECKING:
    pass

menu_emoji_config = EmbedMenuEmojiConfig(delete_message='\N{CROSS MARK}')


class LeaderSkillMenu:
    MENU_TYPE = 'LeaderSkill'
    EMOJI_BUTTON_NAMES = ('\N{HOUSE BUILDING}', char_to_emoji('l'), char_to_emoji('r'), '\N{CROSS MARK}')

    @staticmethod
    def menu():
        transitions = {
            LeaderSkillMenu.EMOJI_BUTTON_NAMES[0]: LeaderSkillMenu.respond_to_house,
            LeaderSkillMenu.EMOJI_BUTTON_NAMES[1]: LeaderSkillMenu.respond_to_l,
            LeaderSkillMenu.EMOJI_BUTTON_NAMES[2]: LeaderSkillMenu.respond_to_r,
        }

        return EmbedMenu(transitions, LeaderSkillMenu.ls_control, menu_emoji_config)

    @staticmethod
    async def respond_to_r(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        # Extract the query from the ls state
        ims['query'] = ims['r_query']
        ims['resolved_monster_id'] = None
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = LeaderSkillMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_to_l(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']

        # Extract the query from the ls state
        ims['query'] = ims['l_query']
        ims['resolved_monster_id'] = None
        id_view_state = await IdViewState.deserialize(dgcog, user_config, ims)
        id_control = LeaderSkillMenu.id_control(id_view_state)
        return id_control

    @staticmethod
    async def respond_to_house(message: Optional[Message], ims, **data):
        dgcog = data['dgcog']
        user_config = data['user_config']
        ls_view_state = await LeaderSkillViewState.deserialize(dgcog, user_config, ims)
        ls_control = LeaderSkillMenu.ls_control(ls_view_state)
        return ls_control

    @staticmethod
    def ls_control(state: LeaderSkillViewState):
        return EmbedControl(
            [LeaderSkillView.embed(state)],
            [emoji_cache.get_by_name(e) for e in LeaderSkillMenu.EMOJI_BUTTON_NAMES]
        )

    @staticmethod
    def id_control(state: IdViewState):
        return EmbedControl(
            [IdView.embed(state)],
            [emoji_cache.get_by_name(e) for e in LeaderSkillMenu.EMOJI_BUTTON_NAMES]
        )
