from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain
from discordmenu.embed.text import BoldText, Text
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.view_state_base import ViewStateBase
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.core.leader_skills import leaderskill_query, ls_multiplier_text

if TYPE_CHECKING:
    pass


class LeaderSkillViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query, l_mon, r_mon, l_query, r_query,
                 l_query_settings, r_query_settings):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None)
        self.l_mon = l_mon
        self.l_query = l_query
        self.l_query_settings = l_query_settings
        self.r_mon = r_mon
        self.r_query = r_query
        self.r_query_settings = r_query_settings

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'l_query': self.l_query,
            'r_query': self.r_query,
            'l_query_settings': self.l_query_settings.serialize(),
            'r_query_settings': self.r_query_settings.serialize()
        })
        return ret

    @staticmethod
    async def deserialize(dbcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        l_query_settings = QuerySettings.deserialize(ims['l_query_settings'])
        r_query_settings = QuerySettings.deserialize(ims['r_query_settings'])

        l_mon, l_query, r_mon, r_query = await leaderskill_query(dbcog, raw_query, ims['original_author_id'])
        return LeaderSkillViewState(original_author_id, menu_type, raw_query, l_mon, r_mon, l_query,
                                    r_query, l_query_settings, r_query_settings)


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
                    BoldText(MonsterHeader.box_with_emoji(state.l_mon, query_settings=state.l_query_settings)),
                    Text(lls.desc if lls else 'None'),
                    BoldText(MonsterHeader.box_with_emoji(state.r_mon, query_settings=state.r_query_settings)),
                    Text(rls.desc if rls else 'None')),
                color=state.l_query_settings.embedcolor),
            embed_footer=embed_footer_with_state(state, qs=state.l_query_settings))
