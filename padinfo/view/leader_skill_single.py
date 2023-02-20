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

from padinfo.core.leader_skills import ls_single_multiplier_text
from padinfo.view.common import get_monster_from_ims

if TYPE_CHECKING:
    pass


class LeaderSkillSingleViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query, query_settings, mon):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None)
        self.mon = mon
        self.query_settings = query_settings

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'query_settings': self.query_settings.serialize()
        })
        return ret

    @staticmethod
    async def deserialize(dbcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        query_settings = QuerySettings.deserialize(ims['query_settings'])

        mon = await get_monster_from_ims(dbcog, ims)
        return LeaderSkillSingleViewState(original_author_id, menu_type,
                                          raw_query, query_settings,
                                          mon)


class LeaderSkillSingleView:
    VIEW_TYPE = 'LeaderSkillSingle'

    @staticmethod
    def embed(state: LeaderSkillSingleViewState):
        ls = state.mon.leader_skill
        return EmbedView(
            embed_main=EmbedMain(
                title=ls_single_multiplier_text(ls),
                description=Box(
                    BoldText(MonsterHeader.box_with_emoji(state.mon, qs=state.query_settings)),
                    Text(ls.desc if ls else 'None')),
                color=state.query_settings.embedcolor),
            embed_footer=embed_footer_with_state(state, qs=state.query_settings))
