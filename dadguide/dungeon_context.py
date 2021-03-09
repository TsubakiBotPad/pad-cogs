from dadguide.database_manager import DadguideDatabase
from dadguide.models.dungeon_model import DungeonModel
from dadguide.models.encounter_model import EncounterModel
from dadguide.models.enemy_data_model import EnemyDataModel
from dadguide.models.enemy_skill_model import EnemySkillModel
from dadguide.models.sub_dungeon_model import SubDungeonModel

dungeon_query = '''
SELECT
sub_dungeons.sub_dungeon_id,
sub_dungeons.dungeon_id,
sub_dungeons.name_ja AS sub_name_ja,
sub_dungeons.name_en AS sub_name_en,
sub_dungeons.name_ko AS sub_name_ko,
dungeons.name_ja,
dungeons.name_en,
dungeons.name_ko,
dungeons.dungeon_type
FROM
sub_dungeons
LEFT OUTER JOIN dungeons on sub_dungeons.dungeon_id = dungeons.dungeon_id
WHERE
dungeons.name_en LIKE "{}%"
ORDER BY
sub_dungeons.sub_dungeon_id
'''

nickname_dungeon_query = '''
SELECT
sub_dungeons.sub_dungeon_id,
sub_dungeons.dungeon_id,
sub_dungeons.name_ja AS sub_name_ja,
sub_dungeons.name_en AS sub_name_en,
sub_dungeons.name_ko AS sub_name_ko,
dungeons.name_ja,
dungeons.name_en,
dungeons.name_ko,
dungeons.dungeon_type
FROM
sub_dungeons
LEFT OUTER JOIN dungeons on sub_dungeons.dungeon_id = dungeons.dungeon_id
WHERE
sub_dungeons.sub_dungeon_id = {}
ORDER BY
sub_dungeons.sub_dungeon_id
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
        if name.lower() in DungeonNickNames:
            results = self.database.query_many(nickname_dungeon_query.format(DungeonNickNames[name]), ())
        else:
            results = self.database.query_many(dungeon_query.format(name), ())
        dungeons = []
        for sd in results:
            sd_model = SubDungeonModel(sd)

        return dungeons

    def get_enemy_skill(self, enemy_skill_id):
        enemy_skill_query = self.database.query_one(skill_query.format(enemy_skill_id), ())
        return EnemySkillModel(enemy_skill_query)

    def get_sub_dungeon_id_from_name(self, dungeon_id, sub_name: str):
        sub_dungeons = self.database.query_many(sub_dungeons_query.format(dungeon_id, sub_name), ())
        if len(sub_dungeons) == 0:
            return 0
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

        



