from padinfo.common.config import UserConfig
from padinfo.core.find_monster import findMonsterCustom


async def get_monster_from_ims(dgcog, ims: dict):
    query = ims.get('query') or ims['raw_query']

    resolved_monster_id_str = ims.get('resolved_monster_id')
    resolved_monster_id = int(resolved_monster_id_str) if resolved_monster_id_str else None
    if resolved_monster_id:
        return dgcog.database.graph.get_monster(resolved_monster_id)
    monster, _, _ = await findMonsterCustom(dgcog, query)
    return monster


def get_reaction_list_from_ims(ims):
    reaction_list_str = ims.get('reaction_list')
    return reaction_list_str.split(',') if reaction_list_str else None
