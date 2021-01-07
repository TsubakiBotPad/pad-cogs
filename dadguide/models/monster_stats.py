from typing import Literal

StatType = Literal['hp', 'atk', 'rcv']


class MonsterStatLatentInput:
    NUM_ATK = 0
    NUM_HP = 0
    NUM_RCV = 0
    NUM_ATKpp = 0
    NUM_HPpp = 0
    NUM_RCVpp = 0
    NUM_ALL_STAT = 0

    def get_multiplier(self, key: StatType):
        if key == 'hp':
            return 1 + self.NUM_HP * 0.015 + self.NUM_HPpp * 0.045 + self.NUM_ALL_STAT * 0.03
        elif key == 'atk':
            return 1 + self.NUM_ATK * 0.01 + self.NUM_ATKpp * 0.03 + self.NUM_ALL_STAT * 0.02
        elif key == 'rcv':
            return 1 + self.NUM_RCV * 0.1 + self.NUM_RCVpp * 0.3 + self.NUM_ALL_STAT * 0.2
        return 1


class MonsterStats:
    def stat(self, monster_model, key: StatType, lv, plus=99, inherit=False, is_plus_297=True,
             stat_latents: MonsterStatLatentInput = None):
        s_min = float(monster_model.stat_values[key]['min'])
        s_max = float(monster_model.stat_values[key]['max'])
        if monster_model.level > 1:
            scale = monster_model.stat_values[key]['scale']
            s_val = s_min + (s_max - s_min) * ((min(lv, monster_model.level) - 1) / (monster_model.level - 1)) ** scale
        else:
            s_val = s_min
        if lv > 99:
            s_val *= 1 + (monster_model.limit_mult / 11 * (lv - 99)) / 100
        plus_dict = {'hp': 10, 'atk': 5, 'rcv': 3}

        if stat_latents:
            s_val *= stat_latents.get_multiplier(key)

        s_val += plus_dict[key] * max(min(plus, 99), 0)
        if inherit:
            inherit_dict = {'hp': 0.10, 'atk': 0.05, 'rcv': 0.15}
            if not is_plus_297:
                s_val -= plus_dict[key] * max(min(plus, 99), 0)
            s_val *= inherit_dict[key]
        return int(round(s_val))

    def stats(self, monster_model, lv=99, plus=0, inherit=False):
        is_plus_297 = False
        if plus == 297:
            plus = (99, 99, 99)
            is_plus_297 = True
        elif plus == 0:
            plus = (0, 0, 0)
        hp = self.stat(monster_model, 'hp', lv, plus[0], inherit, is_plus_297)
        atk = self.stat(monster_model, 'atk', lv, plus[1], inherit, is_plus_297)
        rcv = self.stat(monster_model, 'rcv', lv, plus[2], inherit, is_plus_297)
        weighted = int(round(hp / 10 + atk / 5 + rcv / 3))
        return hp, atk, rcv, weighted


monster_stats = MonsterStats()
