from .base_model import BaseModel


class EnemyDataModel(BaseModel):
    def __init__(self, **kwargs):
        self.enemy_id = kwargs['enemy_id']
        self.behavior = kwargs['behavior']

    def to_dict(self):
        return {
            'enemy_id': self.enemy_id,
            'behavior': self.behavior,
        }
