from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain
from discordmenu.embed.view import EmbedView
from discordmenu.embed.text import BoldText, Text

from padinfo.core.leader_skills import createMultiplierText, createSingleMultiplierText
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view_state.leader_skill import LeaderSkillViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


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


class LeaderSkillSingleView:
    @staticmethod
    def embed(m: "MonsterModel", color):
        ls = m.leader_skill
        return EmbedView(
            EmbedMain(
                title=createSingleMultiplierText(ls),
                description=Box(
                    BoldText(MonsterHeader.name(m, link=True, show_jp=True)),
                    Text(ls.desc if ls else 'None')),
                color=color))
