from padinfo.core.find_monster import findMonsterCustom2
from padinfo.core.id import get_monster_misc_info


async def perform_transforminfo_query(dgcog, raw_query, beta_id3):
    db_context = dgcog.database
    mgraph = dgcog.database.graph
    monster, err, debug_info = await findMonsterCustom2(dgcog, beta_id3, raw_query)

    if not monster:
        return monster, err, debug_info, None, None, None, None

    altversions = mgraph.process_alt_versions(monster.monster_id)
    for mon_id in sorted(altversions):
        if mgraph.monster_is_transform_base_by_id(mon_id):
            transformed_mon = mgraph.get_monster(mgraph.get_next_transform_id_by_monster_id(mon_id))
            if transformed_mon:
                base_mon = mgraph.get_monster(mon_id)
                break

    if not transformed_mon:
        return monster, err, debug_info, transformed_mon, None, None, None

    acquire_raw, _, base_rarity, _, true_evo_type_raw = \
        await get_monster_misc_info(db_context, transformed_mon)

    return base_mon, err, debug_info, transformed_mon, base_rarity, acquire_raw, true_evo_type_raw
