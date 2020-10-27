from dadguide.database_manager import DadguideDatabase
from dadguide.database_context import DbContext
from dadguide.monster_graph import MonsterGraph

database = DadguideDatabase('S:\\Documents\\Games\\PAD\\dadguide.sqlite')
graph = MonsterGraph(database)
db_context = DbContext(database, graph)
graph.set_database(db_context)
graph.build_graph()
db_context.generate_all_monsters()

assert db_context.get_active_skill_query(15)['name_en'] == 'Inferno Breath'
assert db_context.get_leader_skill_query(1202)['name_en'] == 'Fusion Soul'
assert db_context.get_awoken_skill(15)['name_en'] == 'Enhanced Water Orbs'
# print(ctx.get_awoken_skill_ids())
assert db_context.get_monsters_by_awakenings(5)[0].name_en == 'Crystal Aurora Dragon'
assert db_context.get_drop_dungeons(4)[0]['name_en'] == 'Diagoldos Descended!'
assert db_context.monster_is_farmable(4)
assert not db_context.monster_is_farmable(5156)
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

assert db_context.get_monsters_by_awakenings(5)[0].evo_from_id == 26  # check the graph exists in DgMonster
