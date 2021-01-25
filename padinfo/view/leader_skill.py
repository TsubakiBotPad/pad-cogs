from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain
from discordmenu.embed.menu import EmbedView
from discordmenu.embed.text import BoldText, Text

from padinfo.core.leader_skills import createMultiplierText, createSingleMultiplierText
from padinfo.view.components.monster.header import MonsterHeader

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class LeaderSkillView:
    @staticmethod
    def embed(left_m: "MonsterModel", right_m: "MonsterModel", color):
        lls = left_m.leader_skill
        rls = right_m.leader_skill
        return EmbedView(
            EmbedMain(
                title=createMultiplierText(lls, rls),
                description=Box(
                    BoldText(MonsterHeader.name(left_m, link=True, show_jp=True)),
                    Text(lls.desc if lls else 'None'),
                    BoldText(MonsterHeader.name(right_m, link=True, show_jp=True)),
                    Text(rls.desc if rls else 'None')),
                color=color))


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
