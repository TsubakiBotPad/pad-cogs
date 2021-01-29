import csv
from io import StringIO

from json_guff import itsRawMate
from models.EnemySkill import EnemySkill


class EnemySkillDatabase(object):
    def __init__(self, raw_csv: str):
        f = StringIO(itsRawMate(raw_csv))
        reader = csv.reader(f, quotechar='"', delimiter=',',
                            quoting=csv.QUOTE_MINIMAL, skipinitialspace=False)
        count = 0
        enemy_skills = []
        for r in reader:
            if r[0] != 'c':
                params = []
                for i in range(4, len(r)):
                    params.append(r[i])
                es = EnemySkill(int(r[0]), r[1], int(r[2]), r[3], params)
                enemy_skills.append(es)
        self.enemy_skills_dict = {es.id: es for es in enemy_skills}

    def get_es_from_id(self, id):
        return self.enemy_skills_dict[id]