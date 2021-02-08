from padinfo.core.find_monster import findMonsterCustom2


async def perform_transforminfo_query(dgcog, raw_query, beta_id3):
    db_context = dgcog.database
    mgraph = dgcog.database.graph
    found_monster, err, debug_info = await findMonsterCustom2(dgcog, beta_id3, raw_query)

    if not found_monster:
        return found_monster, err, debug_info, None

    altversions = mgraph.process_alt_versions(found_monster.monster_id)
    for mon_id in sorted(altversions):
        if mgraph.monster_is_transform_base_by_id(mon_id):
            transformed_mon = dgcog.get_monster(mgraph.get_next_transform_id_by_monster_id(mon_id))
            if transformed_mon:
                base_mon = dgcog.get_monster(mon_id)
                break

    if not transformed_mon:
        return found_monster, err, debug_info, transformed_mon

    return base_mon, err, debug_info, transformed_mon
