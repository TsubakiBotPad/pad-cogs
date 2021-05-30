from dadguide.database_manager import DadguideDatabase
from dadguide.database_context import DbContext
from dadguide.monster_graph import MonsterGraph
from dadguide.models.enum_types import InternalEvoType

database = DadguideDatabase('S:\\Documents\\Games\\PAD\\dadguide.sqlite')
graph = MonsterGraph(database)
db_context = DbContext(database, graph)
get_monster = lambda mid, server="COMBINED": graph.get_monster(mid, server=server)

assert get_monster(4).is_farmable
assert not get_monster(5156).is_farmable
assert graph.get_base_monster(get_monster(1074)).monster_id == 1073  # evo pandora
assert db_context.get_monsters_by_series(1, server="COMBINED")[0].name_en == 'Tyrra'
assert db_context.get_monsters_by_active(1, server="COMBINED")[0].name_en == 'Tyrra'

# evo types
assert graph.true_evo_type(get_monster(5392)) == InternalEvoType.Ultimate
assert graph.true_evo_type(get_monster(6337)) == InternalEvoType.SuperReincarnated  # sr hades
assert graph.true_evo_type(get_monster(5871)) == InternalEvoType.Pixel  # px sakuya
assert graph.true_evo_type(get_monster(1465)) == InternalEvoType.Normal  # awoken thoth
assert graph.true_evo_type(get_monster(1464)) == InternalEvoType.Base  # base thoth

# mats
assert len(graph.get_evolution(get_monster(3)).mats) == 2
assert 153 in graph.get_evolution(get_monster(3)).mats
