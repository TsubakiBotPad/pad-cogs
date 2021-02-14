from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain
from discordmenu.embed.text import BoldText, Text
from discordmenu.embed.view import EmbedView

from padinfo.core.leader_skills import createSingleMultiplierText
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view_state.leader_skill_single import LeaderSkillSingleViewState

if TYPE_CHECKING:
    pass


class LeaderSkillSingleView:
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
            embed_footer=pad_info_footer_with_state(state))
