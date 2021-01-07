from typing import Literal

StatType = Literal['hp', 'atk', 'rcv']


class MonsterStatModifierInput:
    NUM_ATK = 0
    NUM_HP = 0
    NUM_RCV = 0
    NUM_ATKpp = 0
    NUM_HPpp = 0
    NUM_RCVpp = 0
    NUM_ALL_STAT = 0
    NUM_ATK_AWAKENING = 0
    NUM_HP_AWAKENING = 0
    NUM_RCV_AWAKENING = 0

    def __init__(self, num_atk=0, num_hp=0, num_rcv=0, num_atkpp=0, num_hppp=0, num_rcvpp=0, num_all_stat=0,
                 num_atk_awakening=0, num_hp_awakening=0, num_rcv_awakening=0, num_voice_awakening=0):
        self.NUM_ATK = num_atk
        self.NUM_HP = num_hp
        self.NUM_RCV = num_rcv
        self.NUM_ATKpp = num_atkpp
        self.NUM_HPpp = num_hppp
        self.NUM_RCVpp = num_rcvpp
        self.NUM_ALL_STAT = num_all_stat
        self.NUM_ATK_AWAKENING = num_atk_awakening
        self.NUM_HP_AWAKENING = num_hp_awakening
        self.NUM_RCV_AWAKENING = num_rcv_awakening
        self.NUM_VOICE_AWAKENING = num_voice_awakening

    def get_latent_multiplier(self, key: StatType):
        if key == 'hp':
            return self.NUM_HP * 0.015 + self.NUM_HPpp * 0.045 + self.NUM_ALL_STAT * 0.03
        elif key == 'atk':
            return self.NUM_ATK * 0.01 + self.NUM_ATKpp * 0.03 + self.NUM_ALL_STAT * 0.02
        elif key == 'rcv':
            return self.NUM_RCV * 0.1 + self.NUM_RCVpp * 0.3 + self.NUM_ALL_STAT * 0.2
        return 0

    def get_awakening_addition(self, key: StatType):
        if key == 'hp':
            return 500 * self.NUM_HP_AWAKENING
        elif key == 'atk':
            return 100 * self.NUM_ATK_AWAKENING
        elif key == 'rcv':
            return 200 * self.NUM_RCV_AWAKENING
        return 0


class MonsterStats:
    PLUS_DICT = {'hp': 10, 'atk': 5, 'rcv': 3}

    def stat(self, monster_model, key: StatType, lv, plus=99, inherit=False, is_plus_297=True,
             stat_latents: MonsterStatModifierInput = None):
        s_val = self.base_stat(key, lv, monster_model)

        if stat_latents:
            latents = s_val * stat_latents.get_latent_multiplier(key)
            stat_awakenings = stat_latents.get_awakening_addition(key)
            voice = s_val * stat_latents.NUM_VOICE_AWAKENING * 0.1
            s_val += latents + stat_awakenings + voice

        # include plus calculations. todo: is there a way to do this without subtraction?
        s_val += self.PLUS_DICT[key] * max(min(plus, 99), 0)
        if inherit:
            inherit_dict = {'hp': 0.10, 'atk': 0.05, 'rcv': 0.15}
            if not is_plus_297:
                s_val -= self.PLUS_DICT[key] * max(min(plus, 99), 0)
            s_val *= inherit_dict[key]
        return int(round(s_val))

    def base_stat(self, key, lv, monster_model):
        s_min = float(monster_model.stat_values[key]['min'])
        s_max = float(monster_model.stat_values[key]['max'])
        if monster_model.level > 1:
            scale = monster_model.stat_values[key]['scale']
            s_val = s_min + (s_max - s_min) * ((min(lv, monster_model.level) - 1) / (monster_model.level - 1)) ** scale
        else:
            s_val = s_min
        if lv > 99:
            s_val *= 1 + (monster_model.limit_mult / 11 * (lv - 99)) / 100
        return s_val

    def stats(self, monster_model, lv=99, plus=0, inherit=False, stat_latents: MonsterStatModifierInput = None):
        if not stat_latents:
            stat_latents = MonsterStatModifierInput()

        is_plus_297 = False
        if plus == 297:
            plus = (99, 99, 99)
            is_plus_297 = True
        elif plus == 0:
            plus = (0, 0, 0)

        stat_latents.NUM_VOICE_AWAKENING = len([x for x in monster_model.awakenings if x.awoken_skill_id == 63])

        hp = self.stat(monster_model, 'hp', lv, plus[0], inherit, is_plus_297, stat_latents)
        atk = self.stat(monster_model, 'atk', lv, plus[1], inherit, is_plus_297, stat_latents)
        rcv = self.stat(monster_model, 'rcv', lv, plus[2], inherit, is_plus_297, stat_latents)
        weighted = int(round(hp / 10 + atk / 5 + rcv / 3))
        return hp, atk, rcv, weighted


monster_stats = MonsterStats()
