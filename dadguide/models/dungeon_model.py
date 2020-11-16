from .base_model import BaseModel


class DungeonModel(BaseModel):
    def __init__(self, **kwargs):
        self.dungeon_id = kwargs['dungeon_id']
        self.name_ja = kwargs['name_ja']
        self.name_en = kwargs['name_en']
        self.clean_name_en = self._make_clean_name_en(self.name_en)
        self.name_ko = kwargs['name_ko']

        self.dungeon_type = kwargs['dungeon_type']

    @staticmethod
    def _make_clean_name_en(name):
        if 'tamadra invades in some tech' in name.lower():
            return 'Latents invades some Techs & 20x +Eggs'
        if '1.5x Bonus Pal Point in multiplay' in name:
            name = '[Descends] 1.5x Pal Points in multiplay'
        name = name.replace('No Continues', 'No Cont')
        name = name.replace('No Continue', 'No Cont')
        name = name.replace('Some Limited Time Dungeons', 'Some Guerrillas')
        name = name.replace('are added in', 'in')
        name = name.replace('!', '')
        name = name.replace('Dragon Infestation', 'Dragons')
        name = name.replace(' Infestation', 's')
        name = name.replace('Daily Descended Dungeon', 'Daily Descends')
        name = name.replace('Chance for ', '')
        name = name.replace('Jewel of the Spirit', 'Spirit Jewel')
        name = name.replace(' & ', '/')
        name = name.replace(' / ', '/')
        name = name.replace('PAD Radar', 'PADR')
        name = name.replace('in normal dungeons', 'in normals')
        name = name.replace('Selected ', 'Some ')
        name = name.replace('Enhanced ', 'Enh ')
        name = name.replace('All Att. Req.', 'All Att.')
        name = name.replace('Extreme King Metal Dragon', 'Extreme KMD')
        name = name.replace('Golden Mound-Tricolor [Fr/Wt/Wd Only]', 'Golden Mound')
        name = name.replace('Gods-Awakening Materials Descended', "Awoken Mats")
        name = name.replace('Orb move time 4 sec', '4s move time')
        name = name.replace('Awakening Materials Descended', 'Awkn Mats')
        name = name.replace('Awakening Materials', 'Awkn Mats')
        name = name.replace("Star Treasure Thieves' Den", 'STTD')
        name = name.replace('Ruins of the Star Vault', 'Star Vault')
        name = name.replace('-★6 or lower Enhanced', '')
        return name

    def to_dict(self):
        return {
            'dungeon_id': self.dungeon_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en
        }
