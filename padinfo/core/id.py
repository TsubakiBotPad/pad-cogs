from padinfo.core.find_monster import findMonsterCustom2


async def perform_id_query(dgcog, raw_query, beta_id3):
    db_context = dgcog.database
    monster, _, _ = await findMonsterCustom2(dgcog, beta_id3, raw_query)
    acquire_raw, alt_monsters, base_rarity, transform_base, true_evo_type_raw = \
        await get_monster_misc_info(db_context, monster)

    return monster, transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters


async def perform_evos_query(dgcog, raw_query, beta_id3):
    db_context = dgcog.database
    monster, _, _ = await findMonsterCustom2(dgcog, beta_id3, raw_query)
    alt_versions, gem_versions = await get_monster_evos_info(db_context, monster)
    return monster, alt_versions, gem_versions


async def get_monster_misc_info(db_context, monster):
    transform_base = db_context.graph.get_transform_base(monster)
    true_evo_type_raw = db_context.graph.true_evo_type_by_monster(monster).value
    acquire_raw = db_context.graph.monster_acquisition(monster)
    base_rarity = db_context.graph.get_base_monster_by_id(monster.monster_no).rarity
    alt_monsters = sorted({*db_context.graph.get_alt_monsters_by_id(monster.monster_no)},
                          key=lambda x: x.monster_id)
    return acquire_raw, alt_monsters, base_rarity, transform_base, true_evo_type_raw


async def get_monster_evos_info(db_context, monster):
    alt_versions = sorted({*db_context.graph.get_alt_monsters_by_id(monster.monster_no)},
                          key=lambda x: x.monster_id)
    gem_versions = list(filter(None, map(db_context.graph.evo_gem_monster, alt_versions)))
    return alt_versions, gem_versions
