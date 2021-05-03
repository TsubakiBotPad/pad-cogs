from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain
from discordmenu.embed.text import BoldText, Text
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.config import UserConfig
from padinfo.core.leader_skills import createMultiplierText
from padinfo.core.leader_skills import perform_leaderskill_query
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.view_state_base import ViewStateBase

if TYPE_CHECKING:
    pass


class LeaderSkillViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query, color, l_mon, r_mon, l_query, r_query):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None)
        self.color = color
        self.l_mon = l_mon
        self.l_query = l_query
        self.r_mon = r_mon
        self.r_query = r_query

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'l_query': self.l_query,
            'r_query': self.r_query,
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']

        l_mon, l_query, r_mon, r_query = await perform_leaderskill_query(dgcog, raw_query, ims['original_author_id'])
        return LeaderSkillViewState(original_author_id, menu_type, raw_query, user_config.color, l_mon, r_mon, l_query,
                                    r_query)


class LeaderSkillView:
    VIEW_TYPE = 'LeaderSkill'

    @staticmethod
    def embed(state: LeaderSkillViewState):
        lls = state.l_mon.leader_skill
        rls = state.r_mon.leader_skill
        return EmbedView(
            embed_main=EmbedMain(
                title=createMultiplierText(lls, rls),
                description=Box(
                    BoldText(MonsterHeader.name(state.l_mon, link=True, show_jp=True)),
                    Text(lls.desc if lls else 'None'),
                    BoldText(MonsterHeader.name(state.r_mon, link=True, show_jp=True)),
                    Text(rls.desc if rls else 'None')),
                color=state.color),
            embed_footer=embed_footer_with_state(state))
