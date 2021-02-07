from padinfo.common.config import UserConfig
from padinfo.core.transforminfo import perform_transforminfo_query
from padinfo.view_state.base import ViewState


class TransformInfoViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, color, base_mon, transformed_mon,
        base_rarity, acquire_raw, true_evo_type_raw):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None)
        self.color = color
        self.base_mon = base_mon
        self.transformed_mon = transformed_mon
        self.base_rarity = base_rarity
        self.acquire_raw = acquire_raw
        self.true_evo_type_raw = true_evo_type_raw

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'b_resolved_monster_id': str(self.base_mon.monster_id),
            't_resolved_monster_id': str(self.transformed_mon.monster_id)
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']

        base_mon, _, _, transformed_mon, base_rarity, acquire_raw, true_evo_type_raw = \
            await perform_transforminfo_query(dgcog, raw_query, user_config.beta_id3)
        return TransformInfoViewState(original_author_id, menu_type, raw_query, user_config.color,
                                      base_mon, transformed_mon, base_rarity, acquire_raw,
                                      true_evo_type_raw)
