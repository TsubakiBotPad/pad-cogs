from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain
from discordmenu.embed.text import BoldText, Text
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.config import UserConfig
from padinfo.core.leader_skills import createSingleMultiplierText
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.view_state_base import ViewStateBase
from padinfo.view.common import get_monster_from_ims

if TYPE_CHECKING:
    pass


class LeaderSkillSingleViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query, color, mon):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None)
        self.color = color
        self.mon = mon

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']

        mon = await get_monster_from_ims(dgcog, ims)
        return LeaderSkillSingleViewState(original_author_id, menu_type, raw_query, user_config.color, mon)


class LeaderSkillSingleView:
    VIEW_TYPE = 'LeaderSkillSingle'

    @staticmethod
    def embed(state: LeaderSkillSingleViewState):
        ls = state.mon.leader_skill
        return EmbedView(
            embed_main=EmbedMain(
                title=createSingleMultiplierText(ls),
                description=Box(
                    BoldText(MonsterHeader.name(state.mon, link=True, show_jp=True)),
                    Text(ls.desc if ls else 'None')),
                color=state.color),
            embed_footer=embed_footer_with_state(state))
