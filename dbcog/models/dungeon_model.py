from typing import List

from .base_model import BaseModel
from .sub_dungeon_model import SubDungeonModel


class DungeonModel(BaseModel):
    def __init__(self, sub_dungeon_models: List[SubDungeonModel] = None, **kwargs):
        self.dungeon_id = kwargs['dungeon_id']
        self.name_ja = kwargs['name_ja']
        self.name_en = kwargs['name_en']
        self.clean_name_en = self._make_clean_name_en(self.name_en)
        self.name_ko = kwargs['name_ko']

        self.dungeon_type = kwargs['dungeon_type']
        self.sub_dungeons = sub_dungeon_models

    @staticmethod
    def _make_clean_name_en(name):
        if 'tamadra invades in some tech' in name.lower():
            return 'Latents invades some Techs & 20x +Eggs'
        if '1.5x Bonus Pal Point in multiplay' in name:
            name = '[Descends] 1.5x Pal Points in multiplay'
        clean_name_map = {
            'No Continues': 'No Cont',
            'No Continue': 'No Cont',
            'Some Limited Time Dungeons': 'Some Guerrillas',
            'are added in': 'in',
            '!': '',
            'Dragon Infestation': 'Dragons',
            ' Infestation': 's',
            'Daily Descended Dungeon': 'Daily Descends',
            'Chance for ': '',
            'Jewel of the Spirit': 'Spirit Jewel',
            ' & ': '/',
            ' / ': '/',
            'PAD Radar': 'PADR',
            'in normal dungeons': 'in normals',
            'Selected ': 'Some ',
            'Enhanced ': 'Enh ',
            'All Att. Req.': 'All Att.',
            'Extreme King Metal Dragon': 'Extreme KMD',
            'Golden Mound-Tricolor [Fr/Wt/Wd Only]': 'Golden Mound',
            'Gods-Awakening Materials Descended': "Awoken Mats",
            'Orb move time 4 sec': '4s move time',
            'Awakening Materials Descended': 'Awkn Mats',
            'Awakening Materials': 'Awkn Mats',
            "Star Treasure Thieves' Den": 'STTD',
            'Ruins of the Star Vault': 'Star Vault',
            '-★6 or lower Enhanced': '',
            'Revenge of the ': '',
            'A Gathering of ': '',
            '-Supergravity': '', 
            'Fest Exclusive': 'GFE',
        }
        for find, replace in clean_name_map.items():
            name = name.replace(find, replace)
        return name

    def to_dict(self):
        return {
            'dungeon_id': self.dungeon_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en
        }
