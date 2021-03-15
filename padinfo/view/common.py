async def get_monster_from_ims(dgcog, ims: dict):
    query = ims.get('query') or ims['raw_query']

    resolved_monster_id_str = ims.get('resolved_monster_id')
    resolved_monster_id = int(resolved_monster_id_str) if resolved_monster_id_str else None
    if resolved_monster_id:
        return dgcog.database.graph.get_monster(resolved_monster_id)
    monster = await dgcog.find_monster(query, ims['original_author_id'])
    return monster
