from .base_model import BaseModel


class EvolutionModel(BaseModel):
    def __init__(self, **kwargs):
        self.evolution_type = kwargs['evolution_type']
        self.reversible = bool(kwargs['reversible'])
        self.from_id = kwargs['from_id']
        self.to_id = kwargs['to_id']
        self.mat_1_id = kwargs['mat_1_id']
        self.mat_2_id = kwargs['mat_2_id']
        self.mat_3_id = kwargs['mat_3_id']
        self.mat_4_id = kwargs['mat_4_id']
        self.mat_5_id = kwargs['mat_5_id']
        self.mats = list(filter(None, [self.mat_1_id, self.mat_2_id, self.mat_3_id, self.mat_4_id, self.mat_5_id]))
        self.is_pixel = self.mat_1_id == 3826
        self.is_super_reincarnated = self.mat_1_id == 5077
        self.is_assist = self.mat_1_id == 3911
        self.tstamp = kwargs['tstamp']

    def to_dict(self):
        return {
            'evolution_type': self.evolution_type,
            'from_id': self.from_id,
            'to_id': self.to_id,
        }
