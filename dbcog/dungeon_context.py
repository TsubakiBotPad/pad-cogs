from collections import defaultdict
from functools import lru_cache
from typing import Dict, Iterable, List, Mapping, Optional, Set

from tsutils.enums import Server

from dbcog.database_manager import DBCogDatabase
from dbcog.models.dungeon_model import DungeonModel
from dbcog.models.encounter_model import EncounterModel
from dbcog.models.enemy_data_model import EnemyDataModel
from dbcog.models.enemy_skill_model import EnemySkillModel
from dbcog.models.enum_types import DEFAULT_SERVER
from dbcog.models.monster_model import MonsterModel
from dbcog.models.sub_dungeon_model import SubDungeonModel


def format_with_suffix(text: str, server: Server) -> str:
    suffix_map = {
        Server.COMBINED: '',
        Server.NA: '_na'
    }
    return text.format(suffix_map[server])


NICKNAME_QUERY = '''
SELECT
    enemy_data{0}.behavior,
    encounters.encounter_id,
    encounters.dungeon_id,
    encounters.sub_dungeon_id,
    encounters.enemy_id,
    encounters.monster_id,
    encounters.stage,
    encounters.amount,
    encounters.turns,
    encounters.level,
    encounters.hp,
    encounters.atk,
    encounters.defense,
    sub_dungeons{0}.name_ja AS sub_name_ja,
    sub_dungeons{0}.name_en AS sub_name_en,
    sub_dungeons{0}.name_ko AS sub_name_ko,
    sub_dungeons{0}.technical,
    dungeons{0}.name_ja,
    dungeons{0}.name_en,
    dungeons{0}.name_ko,
    dungeons{0}.dungeon_type
FROM
    encounters
    LEFT OUTER JOIN dungeons on encounters.dungeon_id = dungeons{0}.dungeon_id
    LEFT OUTER JOIN enemy_data{0} on encounters.enemy_id = enemy_data{0}.enemy_id
    LEFT OUTER JOIN monsters{0} on encounters.monster_id = monsters{0}.monster_id
    LEFT OUTER JOIN sub_dungeons on sub_dungeons{0}.sub_dungeon_id = encounters.sub_dungeon_id
WHERE
    encounters.sub_dungeon_id = ?
ORDER BY
    encounters.sub_dungeon_id,
    encounters.stage
'''

SUB_DUNGEON_QUERY = '''
SELECT
    sub_dungeons{0}.sub_dungeon_id,
    sub_dungeons{0}.dungeon_id,
    sub_dungeons{0}.name_ja,
    sub_dungeons{0}.name_en,
    sub_dungeons{0}.name_ko,
    sub_dungeons{0}.technical
FROM
    sub_dungeons{0}
WHERE
    sub_dungeons{0}.dungeon_id = ?
'''

DUNGEON_QUERY = '''
SELECT
    dungeons{0}.dungeon_id,
    dungeons{0}.name_ja,
    dungeons{0}.name_en,
    dungeons{0}.name_ko,
    dungeons{0}.dungeon_type
FROM
    dungeons{0}
WHERE
    dungeons{0}.name_en LIKE ?
'''

ES_QUERY = '''
SELECT
    enemy_skills{0}.enemy_skill_id,
    enemy_skills{0}.name_en,
    enemy_skills{0}.desc_en,
    enemy_skills{0}.desc_en_emoji,
    enemy_skills{0}.min_hits,
    enemy_skills{0}.max_hits,
    enemy_skills{0}.atk_mult
FROM
    enemy_skills{0}
WHERE
    enemy_skills{0}.enemy_skill_id = ?
'''

SUB_DUNGEONS_QUERY_BY_NAME = '''
SELECT
    *
FROM
    sub_dungeons{0}
WHERE 
    sub_dungeons{0}.dungeon_id = ? AND
    sub_dungeons{0}.name_en LIKE ?
ORDER BY
    sub_dungeons{0}.sub_dungeon_id
'''

SUB_DUNGEON_QUERY_BY_INDEX = '''
SELECT
    *
FROM
    sub_dungeons{0}
WHERE
    sub_dungeons{0}.sub_dungeon_id = ?
ORDER BY
    sub_dungeons{0}.sub_dungeon_id
'''

ENCOUNTER_QUERY = '''
SELECT
    encounters.encounter_id,
    encounters.sub_dungeon_id,
    encounters.enemy_id,
    encounters.monster_id,
    encounters.stage,
    encounters.amount,
    encounters.turns,
    encounters.level,
    encounters.hp,
    encounters.atk,
    encounters.defense
FROM
    encounters
WHERE
    encounters.sub_dungeon_id = ?
ORDER BY
    encounters.stage
'''

SPECIFIC_FLOOR_QUERY = '''
SELECT
    encounters.encounter_id,
    encounters.sub_dungeon_id,
    encounters.enemy_id,
    encounters.monster_id,
    encounters.stage,
    encounters.amount,
    encounters.turns,
    encounters.level,
    encounters.hp,
    encounters.atk,
    encounters.defense
FROM
    encounters
WHERE
    encounters.sub_dungeon_id = ?
AND
    encounters.stage = ?
'''

ENEMY_DATA_QUERY = '''
SELECT
    enemy_data{0}.enemy_id,
    enemy_data{0}.behavior
FROM
    enemy_data{0}
WHERE
    enemy_data{0}.enemy_id = ?
'''

MONSTER_DROP_QUERY = '''
SELECT 
    dungeons{0}.dungeon_id,
    sub_dungeons{0}.sub_dungeon_id
FROM 
    drops 
    JOIN monsters{0} ON drops.monster_id = monsters{0}.monster_id 
    JOIN encounters ON drops.encounter_id = encounters.encounter_id 
    JOIN sub_dungeons{0} ON encounters.sub_dungeon_id = sub_dungeons{0}.sub_dungeon_id 
    JOIN dungeons{0} ON sub_dungeons{0}.dungeon_id = dungeons{0}.dungeon_id 
WHERE
    monsters{0}.monster_id = ?
'''

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

DROP_QUERY = """SELECT
  sub_dungeons{0}.sub_dungeon_id
FROM
  sub_dungeons{0}
  JOIN encounters ON encounters.sub_dungeon_id = sub_dungeons{0}.sub_dungeon_id
  JOIN drops ON drops.encounter_id = encounters.encounter_id
WHERE
  drops.monster_id = ?
"""

# TODO: Move to gdoc
DUNGEON_NICKNAMES = {
    'a1': 1022001,
    'arena1': 1022001,
    'bipolar goddess 1': 1022001,
    'bp1': 1022001,
    'a2': 1022002,
    'arena2': 1022002,
    'bipolar goddess 2': 1022002,
    'bp2': 1022002,
    'a3': 1022003,
    'arena3': 1022003,
    'bipolar goddess 3': 1022003,
    'bp3': 1022003,
    'a4': 1022004,
    'arena4': 1022004,
    'three hands of fate': 1022004,
    'thof': 1022004,
    'a5': 1022005,
    'arena5': 1022005,
    'incarnation of worlds': 1022006,
    'iow': 1022006,
    'aa1': 2660001,
    'aa2': 2660002,
    'aa3': 2660003,
    'aa4': 2660004,
    'shura1': 4400001,
    'shura2': 4400002,
    'shura3': 4400003,
    'iwoc': 4400001,
    'alt. iwoc': 4401001,
}


class DungeonContext(object):
    def __init__(self, database: DBCogDatabase):
        self._enemy_data_map: Dict[Server, Dict[int, EnemyDataModel]] = {}
        self._encounter_map: Dict[Server, Dict[int, EncounterModel]] = {}
        self._encounters_by_sub_dungeon_id: Dict[Server, Mapping[int, Set[EncounterModel]]] = {}
        self._sub_dungeon_map: Dict[Server, Dict[int, SubDungeonModel]] = {}
        self._sub_dungeons_by_dungeon_id: Dict[Server, Mapping[int, Set[SubDungeonModel]]] = {}
        self._dungeon_map: Dict[Server, Dict[int, DungeonModel]] = {}

        self.database = database

    def get_dungeons_from_name(self, name: str, *, server: Server) -> List[DungeonModel]:
        dungeons_result = self.database.query_many(format_with_suffix(DUNGEON_QUERY, server), (name + "%",))
        dungeons = []
        for d in dungeons_result:
            dungeons.append(DungeonModel([], **d))

        for dm in dungeons:
            subs = self.database.query_many(format_with_suffix(SUB_DUNGEON_QUERY, server), (dm.dungeon_id,))
            for s in subs:
                encounters = self.database.query_many(format_with_suffix(ENCOUNTER_QUERY, server),
                                                      (s['sub_dungeon_id'],))
                ems = []
                for e in encounters:
                    data = self.database.query_one(format_with_suffix(ENEMY_DATA_QUERY, server), (e["enemy_id"],))
                    if data is not None:
                        edm = EnemyDataModel(**data)
                    else:
                        edm = None
                    ems.append(EncounterModel(edm, **e))
                dm.sub_dungeons.append(SubDungeonModel(ems, **s))
        return dungeons

    def get_dungeons_from_nickname(self, name: str, *, server: Server) -> List[DungeonModel]:
        if name not in DUNGEON_NICKNAMES:
            return []
        sub_id = DUNGEON_NICKNAMES.get(name)
        mega = self.database.query_many(format_with_suffix(NICKNAME_QUERY, server), (sub_id,))
        ems = []
        for enc in mega:
            data = self.database.query_one(format_with_suffix(ENEMY_DATA_QUERY, server), (enc["enemy_id"],))
            if data is not None:
                edm = EnemyDataModel(**data)
            else:
                edm = None
            ems.append(EncounterModel(edm, **enc))
        sm = SubDungeonModel(ems,
                             sub_dungeon_id=mega[0]['sub_dungeon_id'],
                             dungeon_id=mega[0]['dungeon_id'],
                             name_ja=mega[0]['sub_name_ja'],
                             name_en=mega[0]['sub_name_en'],
                             name_ko=mega[0]['sub_name_ko'],
                             technical=mega[0]['technical'])
        return [DungeonModel([sm], **mega[0])]

    def get_floor_from_sub_dungeon(self, sub_id: int, floor: int, *, server: Server) -> List[EncounterModel]:
        floor_query = self.database.query_many(format_with_suffix(SPECIFIC_FLOOR_QUERY, server), (sub_id, floor))
        invade_query = self.database.query_many(format_with_suffix(SPECIFIC_FLOOR_QUERY, server), (sub_id, -1))
        encounter_models = []
        floor_query.extend(invade_query)
        for f in floor_query:
            data = self.database.query_one(format_with_suffix(ENEMY_DATA_QUERY, server), (f['enemy_id'],))
            if data is not None:
                edm = EnemyDataModel(**data)
            else:
                edm = None
            encounter_models.append(EncounterModel(edm, **f))
        return encounter_models

    def get_enemy_skill(self, enemy_skill_id: int, *, server: Server) -> EnemySkillModel:
        enemy_skill_query = self.database.query_one(format_with_suffix(ES_QUERY, server), (enemy_skill_id,))
        return EnemySkillModel(**enemy_skill_query)

    def get_sub_dungeon_id_from_name(self, dungeon_id: int, sub_dungeon_name: Optional[str], *, server: Server = DEFAULT_SERVER) \
            -> Optional[int]:
        if sub_dungeon_name is None:
            sub_dungeon_name = ""
        if sub_dungeon_name.isdigit():
            sub_dungeons = self.database.query_many(format_with_suffix(SUB_DUNGEON_QUERY_BY_INDEX, server),
                                                    (dungeon_id * 1000 + int(sub_dungeon_name),))
        else:
            sub_dungeons = self.database.query_many(format_with_suffix(SUB_DUNGEONS_QUERY_BY_NAME, server),
                                                    (dungeon_id, f"%{sub_dungeon_name}%"))
        if len(sub_dungeons) == 0:
            return None
        elif len(sub_dungeons) > 1:
            if 'plus' in sub_dungeon_name.lower():
                for sd in sub_dungeons:
                    if 'plus' in sd['name_en'].lower():
                        return sd['sub_dungeon_id']
            else:
                for sd in sub_dungeons:
                    if 'plus' not in sd['name_en'].lower():
                        return sd['sub_dungeon_id']
        elif len(sub_dungeons) > 2:
            return 1
        return sub_dungeons[0]['sub_dungeon_id']

    @lru_cache(maxsize=None)
    def get_all_enemy_data(self, *, server: Server = DEFAULT_SERVER) -> List[EnemyDataModel]:
        suffix = ""
        if server == Server.NA:
            pass
            # TODO: There's currently no servers for enemy data.
            # suffix = '_na'

        result = self.database.query_many(f"SELECT * FROM enemy_data{suffix}")
        return [EnemyDataModel(**r) for r in result]

    def get_enemy_data(self, enemy_id: int, *, server: Server = DEFAULT_SERVER) -> Optional[EnemyDataModel]:
        if server not in self._enemy_data_map:
            self._enemy_data_map[server] = {ed.enemy_id: ed for ed in self.get_all_enemy_data(server=server)}
        return self._enemy_data_map[server].get(enemy_id)

    @lru_cache(maxsize=None)
    def get_all_encounters(self, server: Server = DEFAULT_SERVER) -> List[EncounterModel]:
        suffix = ""
        if server == Server.NA:
            pass
            # TODO: There's currently no servers for encounters.
            # suffix = '_na'

        result = self.database.query_many(f"SELECT * FROM encounters{suffix}")
        return [EncounterModel(self.get_enemy_data(r.enemy_id), **r) for r in result]

    def get_encounter(self, encounter_id: int, *, server: Server = DEFAULT_SERVER) -> Optional[EncounterModel]:
        if server not in self._encounter_map:
            self._encounter_map[server] = {e.encounter_id: e for e in self.get_all_encounters(server=server)}
        return self._encounter_map[server].get(encounter_id)

    @lru_cache(maxsize=None)
    def get_all_sub_dungeons(self, server: Server = DEFAULT_SERVER) -> List[SubDungeonModel]:
        if server not in self._encounters_by_sub_dungeon_id:
            self._encounters_by_sub_dungeon_id[server] = defaultdict(set)
            for encounter in self.get_all_encounters(server=server):
                self._encounters_by_sub_dungeon_id[server][encounter.sub_dungeon_id].add(encounter)

        suffix = ""
        if server == Server.NA:
            suffix = '_na'

        result = self.database.query_many(f"SELECT * FROM sub_dungeons{suffix}")
        return [SubDungeonModel(sorted(self._encounters_by_sub_dungeon_id[server][r.sub_dungeon_id],
                                       key=lambda e: e.encounter_id),
                                **r) for r in result]

    def get_sub_dungeon(self, sub_dungeon_id: int, *, server: Server = DEFAULT_SERVER) -> Optional[SubDungeonModel]:
        if server not in self._sub_dungeon_map:
            self._sub_dungeon_map[server] = {e.sub_dungeon_id: e for e in self.get_all_sub_dungeons(server=server)}
        return self._sub_dungeon_map[server].get(sub_dungeon_id)

    @lru_cache(maxsize=None)
    def get_all_dungeons(self, server: Server = DEFAULT_SERVER) -> List[DungeonModel]:
        if server not in self._sub_dungeons_by_dungeon_id:
            self._sub_dungeons_by_dungeon_id[server] = defaultdict(set)
            for sub_dungeon in self.get_all_sub_dungeons(server=server):
                self._sub_dungeons_by_dungeon_id[server][sub_dungeon.dungeon_id].add(sub_dungeon)

        suffix = ""
        if server == Server.NA:
            suffix = '_na'

        result = self.database.query_many(f"SELECT * FROM dungeons{suffix}")
        return [DungeonModel(sorted(self._sub_dungeons_by_dungeon_id[server][r.dungeon_id],
                                    key=lambda sd: sd.sub_dungeon_id),
                             **r) for r in result]

    def get_dungeon(self, dungeon_id: int, *, server: Server = DEFAULT_SERVER) -> Optional[DungeonModel]:
        if server not in self._dungeon_map:
            self._dungeon_map[server] = {e.dungeon_id: e for e in self.get_all_dungeons(server=server)}
        return self._dungeon_map[server].get(dungeon_id)

    @lru_cache(maxsize=None)
    def get_subdungeons_from_drop_monster(self, monster: MonsterModel) -> List[SubDungeonModel]:
        suffix = ""
        if monster.server_priority == Server.NA:
            suffix = '_na'

        rows = self.database.query_many(DROP_QUERY.format(suffix), (monster.monster_id,))
        return [self.get_sub_dungeon(row.sub_dungeon_id, server=monster.server_priority) for row in rows]

    def get_dungeon_mapping(self, subdungeons: Iterable[SubDungeonModel]) -> Mapping[DungeonModel, List[SubDungeonModel]]:
        mapping = defaultdict(list)
        for subdungeon in sorted(subdungeons, key=lambda sd: sd.sub_dungeon_id):
            mapping[self.get_dungeon(subdungeon.dungeon_id)].append(subdungeon)
        return mapping
