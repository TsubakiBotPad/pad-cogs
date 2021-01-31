from padinfo.common.config import UserConfig
from padinfo.core.leader_skills import perform_leaderskill_query
from padinfo.view_state.base import ViewState


class LeaderSkillViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, color, l_mon, r_mon, l_query, r_query):
        self.r_query = r_query
        self.l_query = l_query
        self.menu_type = menu_type
        self.original_author_id = original_author_id
        self.raw_query = raw_query
        self.l_mon = l_mon
        self.r_mon = r_mon
        self.color = color

    def serialize(self):
        ret = {
            'menu_type': self.menu_type,
            'original_author_id': self.original_author_id,
            'raw_query': self.raw_query,
            'l_query': self.l_query,
            'r_query': self.r_query,
        }
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']

        _, l_mon, l_query, _, r_mon, r_query = await perform_leaderskill_query(dgcog, raw_query, user_config.beta_id3)
        return LeaderSkillViewState(original_author_id, menu_type, raw_query, user_config.color, l_mon, r_mon, l_query,
                                    r_query)
