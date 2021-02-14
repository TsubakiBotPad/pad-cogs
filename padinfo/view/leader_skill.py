from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain
from discordmenu.embed.text import BoldText, Text
from discordmenu.embed.view import EmbedView

from padinfo.core.leader_skills import createMultiplierText
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view_state.leader_skill import LeaderSkillViewState

if TYPE_CHECKING:
    pass


class LeaderSkillView:
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
            embed_footer=pad_info_footer_with_state(state))
