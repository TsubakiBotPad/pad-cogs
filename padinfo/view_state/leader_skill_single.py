from padinfo.common.config import UserConfig
from padinfo.view_state.base import ViewStateBase
from padinfo.view_state.common import get_monster_from_ims


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
