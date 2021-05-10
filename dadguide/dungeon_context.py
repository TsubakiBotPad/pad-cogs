from dadguide.database_manager import DadguideDatabase
from dadguide.models.dungeon_model import DungeonModel
from dadguide.models.encounter_model import EncounterModel
from dadguide.models.enemy_data_model import EnemyDataModel
from dadguide.models.enemy_skill_model import EnemySkillModel
from dadguide.models.sub_dungeon_model import SubDungeonModel

nickname_query = '''
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
encounters.sub_dungeon_id = {}
ORDER BY
encounters.sub_dungeon_id,
encounters.stage
'''

sub_dungeon_query = '''
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
sub_dungeons.dungeon_id = {}
'''

dungeon_query = '''
SELECT
dungeons.dungeon_id,
dungeons.name_ja,
dungeons.name_en,
dungeons.name_ko,
dungeons.dungeon_type
FROM
dungeons
WHERE
dungeons.name_en LIKE "{}%"
'''

skill_query = '''
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
enemy_skill_id = {}
'''

sub_dungeons_query = '''
SELECT
sub_dungeons.*
FROM
sub_dungeons
WHERE 
sub_dungeons.dungeon_id = {} AND
sub_dungeons.name_en LIKE "%{}%"
ORDER BY
sub_dungeons.sub_dungeon_id
'''

encounter_query = '''
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
encounters.sub_dungeon_id = {}
ORDER BY
encounters.stage
'''

specific_floor_query = '''
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
encounters.sub_dungeon_id = {}
AND
encounters.stage = {}
'''

enemy_data_query = '''
SELECT
enemy_data.enemy_id,
enemy_data.behavior
FROM
enemy_data
WHERE
enemy_data.enemy_id = {}
'''

DungeonNickNames = {
    'a1': 1022001,
    'arena1': 102201,
    'bipolar goddess 1': 1022001,
    'bp1': 1022001,
    'a2': 1022002,
    'arena2': 102202,
    'bipolar goddess 2': 1022002,
    'bp2': 1022002,
    'a3': 1022003,
    'arena3': 102203,
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
    'shura2': 4401001,
    'iwoc': 4400001,
    'alt. iwoc': 4400001,
}

class DungeonContext(object):
    def __init__(self, database: DadguideDatabase):
        self.database = database

    def get_dungeons_from_name(self, name: str):
        dungeons_result = self.database.query_many(dungeon_query.format(name), ())
        dungeons = []
        for d in dungeons_result:
            dungeons.append(DungeonModel([], **d))

        for dm in dungeons:
            subs = self.database.query_many(sub_dungeon_query.format(dm.dungeon_id), ())
            for s in subs:
                encounters = self.database.query_many(encounter_query.format(s['sub_dungeon_id']), ())
                ems = []
                for e in encounters:
                    data = self.database.query_one(enemy_data_query.format(e["enemy_id"]), ())
                    if data is not None:
                        edm = EnemyDataModel(**data)
                    else:
                        edm = None
                    ems.append(EncounterModel(edm, **e))
                dm.sub_dungeons.append(SubDungeonModel(ems, **s))
        return dungeons

    def get_dungeons_from_nickname(self, name: str):
        if name not in DungeonNickNames:
            return None
        sub_id = DungeonNickNames.get(name)
        mega = self.database.query_many(nickname_query.format(sub_id), ())
        ems = []
        print(mega[0])
        for enc in mega:
            data = self.database.query_one(enemy_data_query.format(enc["enemy_id"]), ())
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

    def get_floor_from_sub_dungeon(self, sub_id, floor):
        floor_query = self.database.query_many(specific_floor_query.format(sub_id, floor), ())
        invade_query = self.database.query_many(specific_floor_query.format(sub_id, -1), ())
        encounter_models = []
        floor_query.extend(invade_query)
        for f in floor_query:
            data = self.database.query_one(enemy_data_query.format(f['enemy_id']), ())
            if data is not None:
                edm = EnemyDataModel(**data)
            else:
                edm = None
            encounter_models.append(EncounterModel(edm, **f))
        return encounter_models



    def get_enemy_skill(self, enemy_skill_id):
        enemy_skill_query = self.database.query_one(skill_query.format(enemy_skill_id), ())
        return EnemySkillModel(**enemy_skill_query)

    def get_sub_dungeon_id_from_name(self, dungeon_id, sub_name: str):
        sub_dungeons = self.database.query_many(sub_dungeons_query.format(dungeon_id, sub_name), ())
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

        



