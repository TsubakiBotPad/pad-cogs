from padinfo.core.find_monster import findMonsterCustom2
from padinfo.core.id import get_monster_misc_info


async def perform_transforminfo_query(dgcog, raw_query, beta_id3):
    db_context = dgcog.database
    bm, err, debug_info = await findMonsterCustom2(dgcog, beta_id3, raw_query)

    if not bm:
        return bm, err, debug_info, None, None, None, None # ????

    tfm = dgcog.database.graph.get_monster(dgcog.database.graph.get_next_transform_id_by_monster(bm))

    if not tfm:
        return bm, err, debug_info, tfm, None, None, None

    return bm, err, debug_info, tfm, base_rarity, acquire_raw, true_evo_type_raw
