from padinfo.core.find_monster import findMonsterCustom2
from padinfo.core.id import get_monster_misc_info


async def perform_transforminfo_query(dgcog, raw_query, beta_id3):
    db_context = dgcog.database
    bm, err, debug_info = await findMonsterCustom2(dgcog, beta_id3, 'transformbase ' + raw_query)
    tfm = dgcog.database.graph.get_monster(dgcog.database.graph.get_next_transform_id_by_monster(bm))
    acquire_raw, _, base_rarity, _, true_evo_type_raw = await get_monster_misc_info(db_context, tfm)

    return bm, err, debug_info, tfm, base_rarity, acquire_raw, true_evo_type_raw
