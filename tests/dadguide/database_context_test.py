from dadguide.database_manager import DadguideDatabase
from dadguide.database_context import DbContext
from dadguide.monster_graph import MonsterGraph
from dadguide.database_manager import EvoType
from dadguide.database_manager import InternalEvoType

database = DadguideDatabase('S:\\Documents\\Games\\PAD\\dadguide.sqlite')
graph = MonsterGraph(database)
db_context = DbContext(database, graph)
graph.set_database(db_context)
graph.build_graph()
db_context.generate_all_monsters()

# print(ctx.get_awoken_skill_ids())
assert db_context.get_monsters_by_awakenings(5)[0].name_en == 'Crystal Aurora Dragon'
assert db_context.graph.monster_is_farmable_by_id(4)
assert not db_context.graph.monster_is_farmable_by_id(5156)
print(db_context.monster_in_rem(1073))  # base pandora
print(db_context.monster_in_rem(2121))
print(db_context.monster_in_pem(2120))  # arthur
assert db_context.monster_in_mp_shop(2256)  # odindra
assert not db_context.monster_in_mp_shop(5156)  # yusuke
assert db_context.get_prev_evolution_by_monster(1074) == 1073  # evo pandora
assert len(db_context.get_next_evolutions_by_monster(1074)) == 2  # evo pandora
assert db_context.get_base_monster_by_id(1074) == 1073 # evo pandora
assert len(db_context.get_evolution_by_material(5963)) == 3  # raziel gem
assert 6352 in db_context.get_evolution_tree_ids(1074)
assert db_context.get_monsters_by_series(1)[0].name_en == 'Tyrra'
assert db_context.get_monsters_by_active(1)[0].name_en == 'Tyrra'
assert db_context.get_monster_evo_gem(
    'Archangel of Knowledge, Raziel', region='en').name_en == 'Archangel of Knowledge, Raziel\'s Gem'

# evo types
# 5392 is mega dkali
assert db_context.graph.get_prev_evolution_by_monster_id(5392) == 1588
assert db_context.graph.cur_evo_type_by_monster_id(5392) == EvoType.UvoAwoken
assert db_context.graph.cur_evo_type_by_monster_id(1587) == EvoType.Base  # base dkali
assert db_context.graph.cur_evo_type_by_monster_id(6238) == EvoType.UuvoReincarnated  # b sam3
assert db_context.graph.cur_evo_type_by_monster_id(3270) == EvoType.UuvoReincarnated  # revo hades
assert db_context.graph.cur_evo_type_by_monster_id(3391) == EvoType.UuvoReincarnated  # revo blodin
assert db_context.graph.cur_evo_type_by_monster_id(1748) == EvoType.UvoAwoken  # awoken hades

assert db_context.graph.true_evo_type_by_monster_id(5392) == InternalEvoType.Ultimate
assert db_context.graph.true_evo_type_by_monster_id(6337) == InternalEvoType.SuperReincarnated  # sr hades
assert db_context.graph.true_evo_type_by_monster_id(5871) == InternalEvoType.Pixel  # px sakuya
assert db_context.graph.true_evo_type_by_monster_id(1465) == InternalEvoType.Normal  # awoken thoth
assert db_context.graph.true_evo_type_by_monster_id(1464) == InternalEvoType.Base  # base thoth
