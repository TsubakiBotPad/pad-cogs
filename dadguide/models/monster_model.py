from .base_model import BaseModel


class MonsterModel(BaseModel):
    def __init__(self, awakenings=None, leader_skill=None, active_skill=None, series=None,
                 is_farmable: bool = False):
        self.awakenings = awakenings
        self.leader_skill = leader_skill
        self.active_skill = active_skill
        self.series = series
        self.is_farmable = is_farmable

    def generate_log(self):
        return {
            'awakenings': self.awakenings,
            'leader_skill': self.leader_skill,
            'active_skill': self.active_skill,
            'series': self.series,
            'is_farmable': self.is_farmable
        }
