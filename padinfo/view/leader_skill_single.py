from typing import TYPE_CHECKING, List, Union, Optional

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.text import BoldText, Text
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.pad_view import PadViewState, PadView
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.core.leader_skills import ls_single_multiplier_text
from padinfo.view.common import get_monster_from_ims

if TYPE_CHECKING:
    pass


class LeaderSkillSingleViewState(PadViewState):
    def __init__(self, original_author_id, menu_type, raw_query, qs: QuerySettings, mon, extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, raw_query, qs, extra_state)
        self.mon = mon

    def serialize(self):
        ret = super().serialize()
        return ret

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        qs = QuerySettings.deserialize(ims['qs'])

        mon = await get_monster_from_ims(dbcog, ims)
        return cls(original_author_id, menu_type,
                   raw_query, qs,
                   mon, ims)


class LeaderSkillSingleView(PadView):
    VIEW_TYPE = 'LeaderSkillSingle'

    @classmethod
    def embed_description(cls, state: LeaderSkillSingleViewState) -> Optional[Union[Box, str]]:
        ls = state.mon.leader_skill
        return Box(
            BoldText(MonsterHeader.box_with_emoji(state.mon, qs=state.qs)),
            Text(ls.desc if ls else 'None'))

    @classmethod
    def embed_title(cls, state: LeaderSkillSingleViewState) -> Optional[str]:
        return ls_single_multiplier_text(state.mon.leader_skill)
