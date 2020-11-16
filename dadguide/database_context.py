from datetime import datetime
from collections import OrderedDict, defaultdict, deque
from typing import Optional

from .database_manager import DadguideDatabase
from .monster_graph import MonsterGraph
from .database_manager import DadguideItem
from .database_manager import DictWithAttrAccess
from .models.scheduled_event_model import ScheduledEventModel
from .models.dungeon_model import DungeonModel


SCHEDULED_EVENT_QUERY = """SELECT
  schedule.*,
  dungeons.name_ja AS d_name_ja,
  dungeons.name_en AS d_name_en,
  dungeons.name_ko AS d_name_ko,
  dungeons.dungeon_type AS dungeon_type
FROM
  schedule LEFT OUTER JOIN dungeons ON schedule.dungeon_id = dungeons.dungeon_id"""


class DbContext(object):
    def __init__(self, database: DadguideDatabase, graph: MonsterGraph):
        self.database = database
        self.graph = graph

    def get_awoken_skill_ids(self):
        SELECT_AWOKEN_SKILL_IDS = 'SELECT awoken_skill_id from awoken_skills'
        return [r.awoken_skill_id for r in
                self.database.query_many(
                    SELECT_AWOKEN_SKILL_IDS, (), DadguideItem, as_generator=True)]

    def get_next_evolutions_by_monster(self, monster_id):
        return self.graph.get_next_evolutions_by_monster_id(monster_id)

    def get_evolution_tree_ids(self, base_monster_id):
        # is not a tree i lied
        base_id = base_monster_id
        evolution_tree = [base_id]
        n_evos = deque()
        n_evos.append(base_id)
        while len(n_evos) > 0:
            n_evo_id = n_evos.popleft()
            for e in self.get_next_evolutions_by_monster(n_evo_id):
                n_evos.append(e)
                evolution_tree.append(e)
        return evolution_tree

    def get_monsters_where(self, f):
        return [m for m in self.get_all_monsters() if f(m)]

    def get_first_monster_where(self, f):
        ms = self.get_monsters_where(f)
        if ms:
            return min(ms, key=lambda m: m.monster_id)

    def get_monsters_by_series(self, series_id: int):
        return self.get_monsters_where(lambda m: m.series_id == series_id)

    def get_monsters_by_active(self, active_skill_id: int):
        return self.get_monsters_where(lambda m: m.active_skill_id == active_skill_id)

    def get_all_monster_ids_query(self, as_generator=True):
        query = self.database.query_many(
            self.database.select_builder(tables={'monsters': ('monster_id',)}), (),
            DictWithAttrAccess,
            as_generator=as_generator)
        if as_generator:
            return map(lambda m: m.monster_id, query)
        return [m.monster_id for m in query]

    def get_all_monsters(self, as_generator=True):
        monsters = (self.graph.get_monster(mid) for mid in self.get_all_monster_ids_query())
        if not as_generator:
            return [*monsters]
        return monsters

    def get_all_events(self) -> ScheduledEventModel:
        result = self.database.query_many(SCHEDULED_EVENT_QUERY, (), DictWithAttrAccess)
        for se in result:
            se['dungeon_model'] = DungeonModel(name_ja=se['d_name_ja'],
                                               name_en=se['d_name_en'],
                                               name_ko=se['d_name_ko'],
                                               **se)
            yield ScheduledEventModel(**se)

    def get_base_monster_ids(self):
        SELECT_BASE_MONSTER_ID = '''
            SELECT evolutions.from_id as monster_id FROM evolutions WHERE evolutions.from_id NOT IN (SELECT DISTINCT evolutions.to_id FROM evolutions)
            UNION
            SELECT monsters.monster_id FROM monsters WHERE monsters.monster_id NOT IN (SELECT evolutions.from_id FROM evolutions UNION SELECT evolutions.to_id FROM evolutions)'''
        return self.database.query_many(
            SELECT_BASE_MONSTER_ID,
            (),
            DictWithAttrAccess,
            as_generator=True)

    def has_database(self):
        return self.database.has_database()

    def close(self):
        self.database.close()
