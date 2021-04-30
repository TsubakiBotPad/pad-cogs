from collections import namedtuple

LIMIT_BREAK_LEVEL = 110

INFO_STRING = """[{}] {}
(Co-op mode)

Without Latents:
Base:    {}
Subattr: {}
Total:   {}

With Latents:
Base:    {}
Subattr: {}
Total:   {}

--------------
{}{}
"""

TEAM_BUTTON_FORMAT = "As {} base ({}x {}): Contributes {}"
CARD_BUTTON_FORMAT = "As {} base ({}x): Deals {}"

MonsterStat = namedtuple('MonsterStat', 'name id mult att')

team_buttons = [
    MonsterStat("Nergi Hunter", 4172, 40, [2, 4]),
    MonsterStat("Oversoul", 5273, 50, [0, 1, 2, 3, 4]),
    MonsterStat("Ryuno Ume", 5252, 80, [2, 4])
]
card_buttons = [
    MonsterStat("Satan", 4286, 300, []),
    MonsterStat("Brachydios", 4134, 350, []),
    MonsterStat("Rajang", 5527, 550, []),
    MonsterStat("Balrog", 5108, 450, [])
]

COLORS = ["R", "B", "G", "L", "D"]


class ButtonInfo:
    def get_info(self, dgcog, monster_model):
        """
        Usage: ^buttoninfo Vajrayasaka

        Shows (main, sub, main+sub)damage x (with | without) atk++ latents

        Optional arguments include:

        [coop|solo], default coop
        e.g:

        button dmg: 7668
        with subattr: 9968.4
        just subattr: whatever

        button dmg with atklatent: 8454.51
        with subattr: 10990.863
        just subattr: whatever
        """
        max_level = LIMIT_BREAK_LEVEL if monster_model.limit_mult != 0 else monster_model.level
        max_atk_latents = monster_model.latent_slots / 2

        sub_attr_multiplier = self._get_sub_attr_multiplier(monster_model)

        result = ButtonInfoResult()
        result.main_damage = self._calculate_damage(dgcog, monster_model, max_level, 0)
        result.sub_damage = result.main_damage * sub_attr_multiplier
        result.total_damage = result.main_damage + result.sub_damage

        result.main_damage_with_atk_latent = self._calculate_damage(dgcog, monster_model, max_level, max_atk_latents)
        result.sub_damage_with_atk_latent = result.main_damage_with_atk_latent * sub_attr_multiplier
        result.total_damage_with_atk_latent = result.main_damage_with_atk_latent + result.sub_damage_with_atk_latent
        return result

    def _calculate_damage(self, dgcog, monster_model, level, num_atkpp_latent=0):
        stat_latents = dgcog.MonsterStatModifierInput(num_atkpp=num_atkpp_latent)
        stat_latents.num_atk_awakening = len([x for x in monster_model.awakenings if x.awoken_skill_id == 1])

        dmg = dgcog.monster_stats.stat(monster_model, 'atk', level, stat_latents=stat_latents)
        num_mult_boost = len([x for x in monster_model.awakenings if x.awoken_skill_id == 30])

        dmg *= 1.5 ** num_mult_boost
        return dmg

    def _get_sub_attr_multiplier(self, monster_model):
        if monster_model.attr2.value == 6 or monster_model.attr1.value == 6:
            return 0
        if monster_model.attr2.value == monster_model.attr1.value:
            return 1 / 10
        return 1 / 3

    def to_string(self, monster, info):
        card_btn_str = self._get_card_btn_damage(card_buttons, info, monster)
        team_btn_str = self._get_team_btn_damage(team_buttons, info, monster)
        return INFO_STRING.format(monster.monster_id, monster.name_en, info.main_damage, info.sub_damage,
                                  info.total_damage,
                                  info.main_damage_with_atk_latent, info.sub_damage_with_atk_latent,
                                  info.total_damage_with_atk_latent, card_btn_str, team_btn_str)

    def _get_card_btn_damage(self, card_buttons, info, monster):
        ret_str = ""
        card_buttons.sort(key=lambda x: x.mult)
        for card in card_buttons:
            ret_str += "\n" + CARD_BUTTON_FORMAT.format(card.name, card.mult,
                                                        (info.main_damage_with_atk_latent * card.mult))
        return ret_str

    def _get_team_btn_damage(self, team_buttons, info, monster):
        # TODO: calculate with oncolor assist damage and ATK+ eq (Oversoul)
        ret_str = ""
        team_buttons.sort(key=lambda x: x.mult)
        for card in team_buttons:
            total_dmg = 0
            if(monster.attr1.value in card.att):
                total_dmg += info.main_damage_with_atk_latent
            if(monster.attr2.value in card.att):
                total_dmg += info.sub_damage_with_atk_latent
            colors_str = ""
            for i in card.att:
                colors_str += COLORS[i]
            ret_str += "\n" + TEAM_BUTTON_FORMAT.format(card.name, card.mult, colors_str, (total_dmg * card.mult))
        return ret_str


class ButtonInfoResult:
    main_damage: float
    total_damage: float
    sub_damage: float
    main_damage_with_atk_latent: float
    total_damage_with_atk_latent: float
    sub_damage_with_atk_latent: float


button_info = ButtonInfo()
