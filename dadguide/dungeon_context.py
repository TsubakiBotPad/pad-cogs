from typing import Optional, List

from dadguide.database_manager import DadguideDatabase
from dadguide.models.dungeon_model import DungeonModel
from dadguide.models.encounter_model import EncounterModel
from dadguide.models.enemy_data_model import EnemyDataModel
from dadguide.models.enemy_skill_model import EnemySkillModel
from dadguide.models.sub_dungeon_model import SubDungeonModel

NICKNAME_QUERY = '''
SELECT
    enemy_data.behavior,
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
    encounters.defence,
    sub_dungeons.name_ja AS sub_name_ja,
    sub_dungeons.name_en AS sub_name_en,
    sub_dungeons.name_ko AS sub_name_ko,
    sub_dungeons.technical,
    dungeons.name_ja,
    dungeons.name_en,
    dungeons.name_ko,
    dungeons.dungeon_type
FROM
    encounters
    LEFT OUTER JOIN dungeons on encounters.dungeon_id = dungeons.dungeon_id
    LEFT OUTER JOIN enemy_data on encounters.enemy_id = enemy_data.enemy_id
    LEFT OUTER JOIN monsters on encounters.monster_id = monsters.monster_id
    LEFT OUTER JOIN sub_dungeons on sub_dungeons.sub_dungeon_id = encounters.sub_dungeon_id
WHERE
    encounters.sub_dungeon_id = ?
ORDER BY
    encounters.sub_dungeon_id,
    encounters.stage
'''

SUB_DUNGEON_QUERY = '''
SELECT
    sub_dungeons.sub_dungeon_id,
    sub_dungeons.dungeon_id,
    sub_dungeons.name_ja,
    sub_dungeons.name_en,
    sub_dungeons.name_ko,
    sub_dungeons.technical
FROM
    sub_dungeons
WHERE
    sub_dungeons.dungeon_id = ?
'''

DUNGEON_QUERY = '''
SELECT
    dungeons.dungeon_id,
    dungeons.name_ja,
    dungeons.name_en,
    dungeons.name_ko,
    dungeons.dungeon_type
FROM
    dungeons
WHERE
    dungeons.name_en LIKE ?
'''

ES_QUERY = '''
SELECT
    enemy_skills.enemy_skill_id,
    enemy_skills.name_en,
    enemy_skills.desc_en,
    enemy_skills.desc_en_emoji,
    enemy_skills.min_hits,
    enemy_skills.max_hits,
    enemy_skills.atk_mult
FROM
    enemy_skills
WHERE
    enemy_skill_id = ?
'''

SUB_DUNGEONS_QUERY_BY_NAME = '''
SELECT
    *
FROM
    sub_dungeons
WHERE 
    sub_dungeons.dungeon_id = ? AND
    sub_dungeons.name_en LIKE ?
ORDER BY
    sub_dungeons.sub_dungeon_id
'''

SUB_DUNGEON_QUERY_BY_INDEX = '''
SELECT
    *
FROM
    sub_dungeons
WHERE
    sub_dungeons.sub_dungeon_id = ?
ORDER BY
    sub_dungeons.sub_dungeon_id
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
    encounters.defence
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
    encounters.defence
FROM
    encounters
WHERE
    encounters.sub_dungeon_id = ?
AND
    encounters.stage = ?
'''

ENEMY_DATA_QUERY = '''
SELECT
    enemy_data.enemy_id,
    enemy_data.behavior
FROM
    enemy_data
WHERE
    enemy_data.enemy_id = ?
'''

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
    def __init__(self, database: DadguideDatabase):
        self.database = database

    def get_dungeons_from_name(self, name: str) -> List[DungeonModel]:
        dungeons_result = self.database.query_many(DUNGEON_QUERY, (name+"%",))
        dungeons = []
        for d in dungeons_result:
            dungeons.append(DungeonModel([], **d))

        for dm in dungeons:
            subs = self.database.query_many(SUB_DUNGEON_QUERY, (dm.dungeon_id,))
            for s in subs:
                encounters = self.database.query_many(ENCOUNTER_QUERY, (s['sub_dungeon_id'],))
                ems = []
                for e in encounters:
                    data = self.database.query_one(ENEMY_DATA_QUERY, (e["enemy_id"],))
                    if data is not None:
                        edm = EnemyDataModel(**data)
                    else:
                        edm = None
                    ems.append(EncounterModel(edm, **e))
                dm.sub_dungeons.append(SubDungeonModel(ems, **s))
        return dungeons

    def get_dungeons_from_nickname(self, name: str) -> List[DungeonModel]:
        if name not in DUNGEON_NICKNAMES:
            return []
        sub_id = DUNGEON_NICKNAMES.get(name)
        mega = self.database.query_many(NICKNAME_QUERY, (sub_id,))
        ems = []
        for enc in mega:
            data = self.database.query_one(ENEMY_DATA_QUERY, (enc["enemy_id"],))
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

    def get_floor_from_sub_dungeon(self, sub_id: int, floor: int) -> List[EncounterModel]:
        floor_query = self.database.query_many(SPECIFIC_FLOOR_QUERY, (sub_id, floor))
        invade_query = self.database.query_many(SPECIFIC_FLOOR_QUERY, (sub_id, -1))
        encounter_models = []
        floor_query.extend(invade_query)
        for f in floor_query:
            data = self.database.query_one(ENEMY_DATA_QUERY, (f['enemy_id'],))
            if data is not None:
                edm = EnemyDataModel(**data)
            else:
                edm = None
            encounter_models.append(EncounterModel(edm, **f))
        return encounter_models

    def get_enemy_skill(self, enemy_skill_id: int) -> EnemySkillModel:
        enemy_skill_query = self.database.query_one(ES_QUERY, (enemy_skill_id,))
        return EnemySkillModel(**enemy_skill_query)

    def get_sub_dungeon_id_from_name(self, dungeon_id: int, sub_name: str) -> Optional[int]:
        if sub_name is None:
            sub_name = ""
        if sub_name.isdigit():
            sub_dungeons = self.database.query_many(SUB_DUNGEON_QUERY_BY_INDEX, (dungeon_id * 1000 + int(sub_name),))
        else:
            sub_dungeons = self.database.query_many(SUB_DUNGEONS_QUERY_BY_NAME, (dungeon_id, f"%{sub_name}%"))
        if len(sub_dungeons) == 0:
            return None
        elif len(sub_dungeons) > 1:
            if 'plus' in sub_name.lower():
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
