from padinfo.common.config import UserConfig
from padinfo.core.id import get_monster_misc_info
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
            'b_resolved_monster_id': self.base_mon.monster_id,
            't_resolved_monster_id': self.transformed_mon.monster_id
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        base_mon_id = ims['b_resolved_monster_id']
        transformed_mon_id = ims['t_resolved_monster_id']

        base_mon = dgcog.get_monster(base_mon_id)
        transformed_mon = dgcog.get_monster(transformed_mon_id)

        acquire_raw, base_rarity, true_evo_type_raw = \
            await TransformInfoViewState.query(dgcog, base_mon, transformed_mon)

        return TransformInfoViewState(original_author_id, menu_type, raw_query, user_config.color,
                                      base_mon, transformed_mon, base_rarity, acquire_raw,
                                      true_evo_type_raw)

    @staticmethod
    async def query(dgcog, base_mon, transformed_mon):
        db_context = dgcog.database
        acquire_raw, _, base_rarity, _, true_evo_type_raw = \
            await get_monster_misc_info(db_context, transformed_mon)

        return acquire_raw, base_rarity, true_evo_type_raw
