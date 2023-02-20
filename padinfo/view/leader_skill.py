from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain
from discordmenu.embed.text import BoldText, Text
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.pad_view import PadViewState
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.core.leader_skills import leaderskill_query, ls_multiplier_text

if TYPE_CHECKING:
    pass


class LeaderSkillViewState(PadViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, qs: QuerySettings,
                 l_mon, r_mon, l_query, r_query,
                 lqs, rqs, extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, query, qs, extra_state)
        self.l_mon = l_mon
        self.l_query = l_query
        self.lqs = lqs
        self.r_mon = r_mon
        self.r_query = r_query
        self.rqs = rqs

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'l_query': self.l_query,
            'r_query': self.r_query,
            'lqs': self.lqs.serialize(),
            'rqs': self.rqs.serialize()
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        lqs = QuerySettings.deserialize(ims['lqs'])
        rqs = QuerySettings.deserialize(ims['rqs'])

        l_mon, l_query, r_mon, r_query = await leaderskill_query(dbcog, raw_query, ims['original_author_id'])

        return cls(original_author_id, menu_type, raw_query, raw_query, lqs,
                   l_mon, r_mon, l_query,
                   r_query, lqs, rqs, ims)


class LeaderSkillView:
    VIEW_TYPE = 'LeaderSkill'

    @staticmethod
    def embed(state: LeaderSkillViewState):
        lls = state.l_mon.leader_skill
        rls = state.r_mon.leader_skill
        return EmbedView(
            embed_main=EmbedMain(
                title=ls_multiplier_text(lls, rls),
                description=Box(
                    BoldText(MonsterHeader.box_with_emoji(state.l_mon, qs=state.lqs)),
                    Text(lls.desc if lls else 'None'),
                    BoldText(MonsterHeader.box_with_emoji(state.r_mon, qs=state.rqs)),
                    Text(rls.desc if rls else 'None')),
                color=state.lqs.embedcolor),
            embed_footer=embed_footer_with_state(state, qs=state.lqs))
