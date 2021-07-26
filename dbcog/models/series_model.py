from .base_model import BaseModel


class SeriesModel(BaseModel):
    def __init__(self, **kwargs):
        self.series_id = kwargs['series_id']
        self.name_ja = kwargs['name_ja']
        self.name_en = kwargs['name_en']
        self.name_ko = kwargs['name_ko']
        self.series_type = kwargs['series_type']

    @property
    def name(self):
        return self.name_en if self.name_en is not None else self.name_ja

    def to_dict(self):
        return {
            'monster_id': self.series_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en,
        }
