from padinfo.common.config import UserConfig
from padinfo.core.transform_info import perform_transforminfo_query
from padinfo.core.id import get_monster_misc_info


class TransformInfoViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, color, b_mon, t_mon,
        base_rarity, acquire_raw, true_evo_type_raw):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None)
        self.color = color
        self.b_mon = b_mon
        self.t_mon = t_mon
        # self.query = query
        self.base_rarity = base_rarity
        self.acquire_raw = acquire_raw
        self.true_evo_type_raw = true_evo_type_raw

    def serialize(self):
        ret = super().serialize()
        ret.update({
            # 'query': self.query
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']

        # just doing this to imitate ./id.py....
        query = ims.get('query') or raw_query

        b_mon, t_mon, base_rarity, acquire_raw, true_evo_type_raw = await perform_transforminfo_query(dgcog,
            raw_query, user_config.beta_id3)
        return TransformInfoViewState(original_author_id, menu_type, raw_query, user_config.color, b_mon,
            t_mon, query, base_rarity, acquire_raw, true_evo_type_raw)
