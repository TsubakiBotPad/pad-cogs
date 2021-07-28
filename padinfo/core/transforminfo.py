async def perform_transforminfo_query(dbcog, raw_query, author_id):
    db_context = dbcog.database
    mgraph = dbcog.database.graph
    found_monster = await dbcog.find_monster(raw_query, author_id)

    if not found_monster:
        return None, None, None

    transformed_mon = None
    base_mon = None
    altversions = mgraph.get_alt_monsters(found_monster)
    for mon in altversions:
        if mgraph.monster_is_transform_base(mon):
            transformed_mon = mgraph.get_next_transform(mon)
            if transformed_mon:
                base_mon = mon
                break

    if not transformed_mon:
        return found_monster, None, None

    reaction_ids = [base_mon.monster_id, transformed_mon.monster_id]
    current = transformed_mon
    while True:
        next_transform = mgraph.get_next_transform(current)
        if next_transform is not None and next_transform.monster_id not in reaction_ids:
            reaction_ids.append(next_transform.monster_id)
            current = next_transform
        else:
            break

    return base_mon, transformed_mon, reaction_ids
