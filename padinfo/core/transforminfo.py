async def perform_transforminfo_query(dgcog, raw_query, author_id):
    db_context = dgcog.database
    mgraph = dgcog.database.graph
    found_monster = await dgcog.find_monster(raw_query, author_id)

    if not found_monster:
        return None, None, None

    transformed_mon = None
    base_mon = None
    altversions = mgraph.process_alt_versions(found_monster.monster_id)
    for mon_id in altversions:
        if mgraph.monster_is_transform_base_by_id(mon_id):
            transformed_mon = dgcog.get_monster(mgraph.get_next_transform_id_by_monster_id(mon_id))
            if transformed_mon:
                base_mon = dgcog.get_monster(mon_id)
                break

    if not transformed_mon:
        return found_monster, None, None

    reaction_ids = [base_mon.monster_id, transformed_mon.monster_id]
    current_id = transformed_mon.monster_id
    while True:
        next_transform_id = mgraph.get_next_transform_id_by_monster_id(current_id)
        if next_transform_id is not None and next_transform_id not in reaction_ids:
            reaction_ids.append(next_transform_id)
            current_id = next_transform_id
        else:
            break

    return base_mon, transformed_mon, reaction_ids
