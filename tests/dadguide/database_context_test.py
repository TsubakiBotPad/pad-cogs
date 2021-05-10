from dadguide.database_manager import DadguideDatabase
from dadguide.database_context import DbContext
from dadguide.monster_graph import MonsterGraph
from dadguide.models.enum_types import InternalEvoType

database = DadguideDatabase('S:\\Documents\\Games\\PAD\\dadguide.sqlite')
graph = MonsterGraph(database)
db_context = DbContext(database, graph)

# print(ctx.get_awoken_skill_ids())
assert db_context.graph.monster_is_farmable_by_id(4)
assert not db_context.graph.monster_is_farmable_by_id(5156)
assert db_context.graph.get_base_monster_by_id(1074).monster_id == 1073  # evo pandora
assert db_context.get_monsters_by_series(1)[0].name_en == 'Tyrra'
assert db_context.get_monsters_by_active(1)[0].name_en == 'Tyrra'

# evo types
# 5392 is mega dkali
assert db_context.graph.get_prev_evolution_id_by_monster_id(5392) == 1588

assert db_context.graph.true_evo_type_by_monster_id(5392) == InternalEvoType.Ultimate
assert db_context.graph.true_evo_type_by_monster_id(6337) == InternalEvoType.SuperReincarnated  # sr hades
assert db_context.graph.true_evo_type_by_monster_id(5871) == InternalEvoType.Pixel  # px sakuya
assert db_context.graph.true_evo_type_by_monster_id(1465) == InternalEvoType.Normal  # awoken thoth
assert db_context.graph.true_evo_type_by_monster_id(1464) == InternalEvoType.Base  # base thoth

# check that we're using the most recent data
assert db_context.graph.true_evo_type_by_monster_id(3908) == InternalEvoType.Reincarnated  # revo typhon

assert len(db_context.graph.get_evo_by_monster_id(3).mats) == 2
assert 153 in db_context.graph.get_evo_by_monster_id(3).mats
