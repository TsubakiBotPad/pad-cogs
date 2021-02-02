import csv
import json
from io import StringIO

from dungeon.json_guff import itsRawMate
from dungeon.models.EnemySkill import EnemySkill


class EnemySkillDatabase(object):
    def __init__(self, json_csv: str):
        with open(json_csv, encoding='utf-8') as file:
            data = json.load(file)
        f = StringIO(itsRawMate(data['enemy_skills']))
        reader = csv.reader(f, quotechar='"', delimiter=',',
                            quoting=csv.QUOTE_MINIMAL, skipinitialspace=False)
        count = 0
        enemy_skills = []
        for r in reader:
            if r[0] != 'c':
                params = []
                for i in range(4, len(r)):
                    params.append(r[i])
                es = EnemySkill(r)
                enemy_skills.append(es)
        self.enemy_skills_dict = {es.enemy_skill_id: es for es in enemy_skills}

    def get_es_from_id(self, id):
        return self.enemy_skills_dict[id]