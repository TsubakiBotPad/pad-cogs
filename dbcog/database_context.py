from functools import lru_cache
from typing import Callable, Hashable, Iterable, List, Optional

from tsutils.enums import Server

from .database_manager import DBCogDatabase
from .dungeon_context import DungeonContext
from .models.awoken_skill_model import AwokenSkillModel
from .models.dungeon_model import DungeonModel
from .models.enum_types import DEFAULT_SERVER
from .models.monster_model import MonsterModel
from .models.scheduled_event_model import ScheduledEventModel
from .models.series_model import SeriesModel
from .monster_graph import MonsterGraph

SCHEDULED_EVENT_QUERY = """SELECT
  schedule.*,
  dungeons.name_ja AS d_name_ja,
  dungeons.name_en AS d_name_en,
  dungeons.name_ko AS d_name_ko,
  dungeons.dungeon_type AS dungeon_type
FROM
  schedule 
  LEFT JOIN dungeons ON schedule.dungeon_id = dungeons.dungeon_id
"""


class DbContext:
    def __init__(self, database: DBCogDatabase, graph: MonsterGraph, dungeon: DungeonContext,
                 debug_monster_ids: Optional[List[int]] = None):
        self.database = database
        self.graph = graph
        self.dungeon = dungeon

        self.cached_filters = {}
        self.debug_monster_ids = debug_monster_ids

        self.awoken_skill_map = {awsk.awoken_skill_id: awsk for awsk in self.get_all_awoken_skills()}
        self.series_map = {series.series_id: series for series in self.get_all_series()}

    def get_monsters_where(self, f: Callable[[MonsterModel], bool], *, server: Server, cache_key: Hashable = None) \
            -> List[MonsterModel]:
        if cache_key is None:
            return [m for m in self.get_all_monsters(server) if f(m)]

        if (cache_key, server) in self.cached_filters:
            return self.cached_filters[(cache_key, server)]

        self.cached_filters[(cache_key, server)] = self.get_monsters_where(f, server=server)
        return self.cached_filters[(cache_key, server)]

    def get_monsters_by_series(self, series_id: int, *, server: Server) -> List[MonsterModel]:
        return self.get_monsters_where(lambda m: m.series_id == series_id, server=server)

    def get_monsters_by_active(self, active_skill_id: int, *, server: Server) -> List[MonsterModel]:
        return self.get_monsters_where(lambda m: m.active_skill_id == active_skill_id, server=server)

    def get_monsters_by_leader(self, leader_skill_id: int, *, server: Server) -> List[MonsterModel]:
        return self.get_monsters_where(lambda m: m.leader_skill_id == leader_skill_id, server=server)

    def get_all_monster_ids(self, server: Server) -> Iterable[int]:
        # We don't need to query if we're in debug mode.  We already know exactly which monsters we're working with
        if self.debug_monster_ids is not None:
            return self.debug_monster_ids

        suffix = '_na' if server == Server.NA else ''
        query = self.database.query_many(f"SELECT monster_id FROM monsters{suffix}", as_generator=True)
        return (m.monster_id for m in query)

    def get_all_monsters(self, server: Server = DEFAULT_SERVER) -> List[MonsterModel]:
        return [self.graph.get_monster(mid, server=server) for mid in self.get_all_monster_ids(server)]

    def get_all_awoken_skills(self) -> List[AwokenSkillModel]:
        result = self.database.query_many("SELECT * FROM awoken_skills")
        return [AwokenSkillModel(**r) for r in result]

    def get_all_series(self) -> List[SeriesModel]:
        result = self.database.query_many("SELECT * FROM series")
        return [SeriesModel(**r) for r in result]

    def get_all_events(self) -> Iterable[ScheduledEventModel]:
        result = self.database.query_many(SCHEDULED_EVENT_QUERY)
        for se in result:
            se['dungeon_model'] = DungeonModel(name_ja=se['d_name_ja'],
                                               name_en=se['d_name_en'],
                                               name_ko=se['d_name_ko'],
                                               **se)
            yield ScheduledEventModel(**se)

    def has_database(self) -> bool:
        return self.database.has_database()

    def close(self) -> None:
        self.database.close()
