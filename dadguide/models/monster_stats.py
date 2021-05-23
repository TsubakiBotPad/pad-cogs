from typing import Literal
from dadguide.token_mappings import AwokenSkills

StatType = Literal['hp', 'atk', 'rcv']


class MonsterStatModifierInput:
    def __init__(self, num_hp=0, num_atk=0, num_rcv=0, num_hppp=0, num_atkpp=0, num_rcvpp=0, num_all_stat=0,
                 num_hp_awakening=0, num_atk_awakening=0, num_rcv_awakening=0, num_voice_awakening=0):
        self.num_hp = num_hp
        self.num_atk = num_atk
        self.num_rcv = num_rcv
        self.num_hppp = num_hppp
        self.num_atkpp = num_atkpp
        self.num_rcvpp = num_rcvpp
        self.num_all_stat = num_all_stat
        self.num_hp_awakening = num_hp_awakening
        self.num_atk_awakening = num_atk_awakening
        self.num_rcv_awakening = num_rcv_awakening
        self.num_voice_awakening = num_voice_awakening

    def get_latent_multiplier(self, key: StatType):
        if key == 'hp':
            return self.num_hp * 0.015 + self.num_hppp * 0.045 + self.num_all_stat * 0.03
        elif key == 'atk':
            return self.num_atk * 0.01 + self.num_atkpp * 0.03 + self.num_all_stat * 0.02
        elif key == 'rcv':
            return self.num_rcv * 0.1 + self.num_rcvpp * 0.3 + self.num_all_stat * 0.2
        return 0

    def get_awakening_addition(self, key: StatType):
        if key == 'hp':
            return 500 * self.num_hp_awakening
        elif key == 'atk':
            return 100 * self.num_atk_awakening
        elif key == 'rcv':
            return 200 * self.num_rcv_awakening
        return 0


class MonsterStats:
    PLUS_DICT = {'hp': 10, 'atk': 5, 'rcv': 3}
    LV_120_MULT_DICT = {'hp': 10, 'atk': 5, 'rcv': 5}

    def stat(self, monster_model, key: StatType, lv, *, plus=99, inherit=False, is_plus_297=True,
             stat_latents: MonsterStatModifierInput = None, multiplayer=False, inherited_monster: "MonsterModel" = None, inherited_monster_lvl=99):
        # TODO: deal with atk-, rcv-, and hp- awakenings
        # PAD rounds stats from the start before any calculations
        s_val = round(self.base_stat(key, lv, monster_model))
        if stat_latents and not (monster_model.is_equip or inherit):
            latents = s_val * stat_latents.get_latent_multiplier(key)
            stat_awakenings = stat_latents.get_awakening_addition(key)
            voice = s_val * stat_latents.num_voice_awakening * 0.1
            s_val += latents + stat_awakenings + voice

        # include plus calculations. todo: is there a way to do this without subtraction?
        s_val += self.PLUS_DICT[key] * max(min(plus, 99), 0)
        if inherit:
            inherit_dict = {'hp': 0.10, 'atk': 0.05, 'rcv': 0.15}
            if not is_plus_297:
                s_val -= self.PLUS_DICT[key] * max(min(plus, 99), 0)
            s_val *= inherit_dict[key]

        if inherited_monster:
            # add base stats of inherit only if main atts are the same and not no-main-att
            if monster_model.attr1.value == inherited_monster.attr1.value or monster_model.attr1.value == 6 or inherited_monster.attr1.value == 6:
                # recursion is not possible because inherits do not have inherits on top of them
                # inherit=True to calculate inherit stats and multiplayer=False in case the inherit has a multiboost awakening
                s_val += round(self.stat(inherited_monster, key, inherited_monster_lvl,
                                   inherit=True, multiplayer=False))
            # add bonus atk, hp, or rcv awakenings
            inherit_bonus = MonsterStatModifierInput(
                num_hp_awakening=inherited_monster.awakening_count(AwokenSkills.ENHANCEDHP.value),
                num_atk_awakening=inherited_monster.awakening_count(AwokenSkills.ENHANCEDATK.value),
                num_rcv_awakening=inherited_monster.awakening_count(AwokenSkills.ENHANCEDRCV.value)
            )
            s_val += inherit_bonus.get_awakening_addition(key)

        if multiplayer:
            print(s_val)
            num_multiboost = monster_model.awakening_count(AwokenSkills.MULTIBOOST.value)
            num_multiboost += inherited_monster.awakening_count(
                AwokenSkills.MULTIBOOST.value) if inherited_monster else 0
            s_val = round(round(s_val) * (1.5 ** num_multiboost))
            print(s_val)

        return s_val

    def base_stat(self, key, lv, monster_model):
        s_min = float(monster_model.stat_values[key]['min'])
        s_max = float(monster_model.stat_values[key]['max'])
        if monster_model.level > 1:
            scale = monster_model.stat_values[key]['scale']
            s_val = s_min + (s_max - s_min) * ((min(lv, monster_model.level) - 1) /
                                               (monster_model.level - 1)) ** scale
        else:
            s_val = s_min
        val_at_99 = s_val
        if 99 < lv:
            s_val *= 1 + (monster_model.limit_mult / 11 * (min(lv, 110) - 99)) / 100
        if 110 < lv:
            slb_bonus = self.LV_120_MULT_DICT[key] * val_at_99 * (lv-110) / 1000
            s_val += slb_bonus
        return s_val

    def stats(self, monster_model, lv=99, plus=0, inherit=False, stat_latents: MonsterStatModifierInput = None):
        is_plus_297 = False
        if plus == 297:
            plus = (99, 99, 99)
            is_plus_297 = True
        elif plus == 0:
            plus = (0, 0, 0)

        if not stat_latents:
            stat_latents = MonsterStatModifierInput(
                num_hp_awakening=monster_model.awakening_count(AwokenSkills.ENHANCEDHP.value),
                num_atk_awakening=monster_model.awakening_count(AwokenSkills.ENHANCEDATK.value),
                num_rcv_awakening=monster_model.awakening_count(AwokenSkills.ENHANCEDRCV.value),
                num_voice_awakening=monster_model.awakening_count(AwokenSkills.VOICE.value)
            )
        # TODO: Fix rounding
        hp = int(round(self.stat(monster_model, 'hp', lv,
                 plus=plus[0], inherit=inherit, is_plus_297=is_plus_297, stat_latents=stat_latents)))
        atk = int(round(self.stat(monster_model, 'atk', lv,
                  plus=plus[1], inherit=inherit, is_plus_297=is_plus_297, stat_latents=stat_latents)))
        rcv = int(round(self.stat(monster_model, 'rcv', lv,
                  plus=plus[2], inherit=inherit, is_plus_297=is_plus_297, stat_latents=stat_latents)))
        weighted = int(round(hp / 10 + atk / 5 + rcv / 3))
        return hp, atk, rcv, weighted


monster_stats = MonsterStats()
