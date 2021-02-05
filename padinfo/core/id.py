from padinfo.common.external_links import ilmina_skill
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


async def perform_mats_query(dgcog, raw_query, beta_id3):
    db_context = dgcog.database
    monster, _, _ = await findMonsterCustom2(dgcog, beta_id3, raw_query)
    mats = db_context.graph.evo_mats_by_monster(monster)
    usedin = db_context.graph.material_of_monsters(monster)
    evo_gem = db_context.graph.evo_gem_monster(monster)
    gemid = str(evo_gem.monster_no_na) if evo_gem else None
    gemusedin = db_context.graph.material_of_monsters(evo_gem) if evo_gem else []
    skillups = []
    skillup_evo_count = 0
    link = ilmina_skill(monster)

    if monster.active_skill:
        sums = [m for m in db_context.get_monsters_by_active(monster.active_skill.active_skill_id)
                if db_context.graph.monster_is_farmable_evo(m)]
        sugs = [db_context.graph.evo_gem_monster(su) for su in sums]
        vsums = []
        for su in sums:
            if not any(susu in vsums for susu in db_context.graph.get_alt_monsters(su)):
                vsums.append(su)
        skillups = [su for su in vsums
                    if db_context.graph.monster_is_farmable_evo(su) and
                    db_context.graph.get_base_id(su) != db_context.graph.get_base_id(monster) and
                    su not in sugs] if monster.active_skill else []
        skillup_evo_count = len(sums) - len(vsums)

    if not any([mats, usedin, gemusedin, skillups and not monster.is_stackable]):
        return None, None, None, None, None, None, None, None

    return monster, mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link



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
