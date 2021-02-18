from padinfo.core.find_monster import findMonsterCustom


async def get_monster_from_ims(dgcog, ims: dict):
    query = ims.get('query') or ims['raw_query']

    resolved_monster_id_str = ims.get('resolved_monster_id')
    resolved_monster_id = int(resolved_monster_id_str) if resolved_monster_id_str else None
    if resolved_monster_id:
        return dgcog.database.graph.get_monster(resolved_monster_id)
    monster, _, _ = await findMonsterCustom(dgcog, query)
    return monster
