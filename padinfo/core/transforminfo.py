from padinfo.core.find_monster import find_monster


async def perform_transforminfo_query(dgcog, raw_query):
    db_context = dgcog.database
    mgraph = dgcog.database.graph
    found_monster = await find_monster(dgcog, raw_query)

    if not found_monster:
        return None, None

    transformed_mon = None
    base_mon = None
    altversions = mgraph.process_alt_versions(found_monster.monster_id)
    for mon_id in sorted(altversions):
        if mgraph.monster_is_transform_base_by_id(mon_id):
            transformed_mon = dgcog.get_monster(mgraph.get_next_transform_id_by_monster_id(mon_id))
            if transformed_mon:
                base_mon = dgcog.get_monster(mon_id)
                break

    if not transformed_mon:
        return found_monster, transformed_mon

    return base_mon, transformed_mon
