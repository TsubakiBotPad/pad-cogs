from tsutils.enums import Server

from dbcog.database_manager import DBCogDatabase
from dbcog.database_context import DbContext
from dbcog.dungeon_context import DungeonContext
from dbcog.monster_graph import MonsterGraph
from dbcog.models.enum_types import InternalEvoType

database = DBCogDatabase('S:\\Documents\\Games\\PAD\\dadguide.sqlite')
graph = MonsterGraph(database)
dungeon = DungeonContext(database)
dungeon = DungeonContext(database)
db_context = DbContext(database, graph, dungeon)
get_monster = lambda mid, server=Server.COMBINED: graph.get_monster(mid, server=server)

assert get_monster(4).is_farmable
assert not get_monster(5156).is_farmable
assert graph.get_base_monster(get_monster(1074)).monster_id == 1073  # evo pandora
assert db_context.get_monsters_by_series(1, server=Server.COMBINED)[0].name_en == 'Tyrra'
assert db_context.get_monsters_by_active(1, server=Server.COMBINED)[0].name_en == 'Tyrra'

# evo types
assert graph.true_evo_type(get_monster(5392)) == InternalEvoType.Ultimate
assert graph.true_evo_type(get_monster(6337)) == InternalEvoType.SuperReincarnated  # sr hades
assert graph.true_evo_type(get_monster(5871)) == InternalEvoType.Pixel  # px sakuya
assert graph.true_evo_type(get_monster(1465)) == InternalEvoType.Normal  # awoken thoth
assert graph.true_evo_type(get_monster(1464)) == InternalEvoType.Base  # base thoth

# mats
assert len(graph.get_evolution(get_monster(3)).mats) == 2
assert 153 in graph.get_evolution(get_monster(3)).mats
