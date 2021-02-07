from padinfo.common.config import UserConfig
from padinfo.core.find_monster import findMonsterCustom2


async def get_monster_from_ims(dgcog, user_config: UserConfig, ims: dict):
    raw_query = ims['raw_query']

    resolved_monster_id_str = ims.get('resolved_monster_id')
    resolved_monster_id = int(resolved_monster_id_str) if resolved_monster_id_str else None
    if resolved_monster_id:
        return dgcog.database.graph.get_monster(resolved_monster_id)
    monster, _, _ = await findMonsterCustom2(dgcog, user_config.beta_id3, raw_query)
    return monster
