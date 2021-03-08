from dadguide.database_manager import DadguideDatabase
from dadguide.models.dungeon_model import DungeonModel
from dadguide.models.encounter_model import EncounterModel
from dadguide.models.enemy_data_model import EnemyDataModel

mega_query = '''
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
dungeons.name_en LIKE "{}%"
ORDER BY
encounters.sub_dungeon_id,
encounters.stage
'''

skill_query = '''
SELECT
enemy_skills.*
FROM
enemy_skills
WHERE
enemy_skill_id = {}
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
    'arena4': 102204,
    'three hands of fate': 1022004,
    'thof': 1022004,
    'a5': 1022005,
    'arena5': 102205,
    'incarnation of worlds': 1022005,
    'iow': 1022005,
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

    def get_dungeon_from_name(self, name: str):
        mega = self.database.query_many(mega_query.format(name), ())
        if len(mega) == 0:
            return None
        dungeon_dict = {}
        dungeons = []
        for m in mega:
            em = EncounterModel(
                EnemyDataModel(m),
                m
            )
            if len(dungeon_dict) == 0:
                dungeon_dict.update({m['dungeon_id']: [em]})
            else:
                dungeon_dict.get(m['dungeon_id']).append(em)

        for dungeon in dungeon_dict.keys():
            encounter_models = dungeon_dict.get(dungeon)
            dungeons.append(DungeonModel(encounter_models, encounter_models[0]))
        return dungeons

    def get_enemy_skill(self, enemy_skill_id):
        



