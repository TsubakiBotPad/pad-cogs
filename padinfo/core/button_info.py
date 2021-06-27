from collections import namedtuple

LIMIT_BREAK_LEVEL = 110
SUPER_LIMIT_BREAK_LEVEL = 120

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
Inherits are assumed to be the max possible level (up to 110) and +297
{}
{}
"""

TEAM_BUTTON_FORMAT = "[{}] {} ({}x {}): {}"
CARD_BUTTON_FORMAT = "[{}] {} ({}x): {}"

MonsterStat = namedtuple('MonsterStat', 'name id mult att')

TEAM_BUTTONS = [
    # account for attributes when spacing
    MonsterStat("Nergi Hunter{}", 4172, 40, [2, 4]),
    MonsterStat("Oversoul{} ", 5273, 50, [0, 1, 2, 3, 4]),
    MonsterStat("Ryuno Ume{}   ", 5252, 80, [2, 4])
]
CARD_BUTTONS = [
    MonsterStat("Satan{}        ", 4286, 300, []),
    MonsterStat("Durandalf Eq{} ", 4723, 300, []),
    MonsterStat("Brachydios Eq{}", 4152, 350, []),
    MonsterStat("Rajang Eq{}    ", 5530, 550, []),
    MonsterStat("Balrog{}       ", 5108, 450, [])
]

COLORS = ["R", "B", "G", "L", "D"]
NIL_ATT = 'Nil'


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
        slb_level = SUPER_LIMIT_BREAK_LEVEL if monster_model.limit_mult != 0 else None
        max_atk_latents = monster_model.latent_slots / 2

        sub_attr_multiplier = self._get_sub_attr_multiplier(monster_model)

        result = ButtonInfoResult()
        result.main_damage = self._calculate_damage(dgcog, monster_model, max_level)
        result.sub_damage = result.main_damage * sub_attr_multiplier
        result.total_damage = result.main_damage + result.sub_damage
        if slb_level is None:
            result.main_slb_damage = None
            result.sub_slb_damage = None
            result.total_slb_damage = None
        else:
            result.main_slb_damage = self._calculate_damage(dgcog, monster_model, slb_level)
            result.sub_slb_damage = result.main_slb_damage * sub_attr_multiplier
            result.total_slb_damage = result.main_slb_damage + result.sub_slb_damage

        result.main_damage_with_atk_latent = self._calculate_damage(
            dgcog, monster_model, max_level, num_atkplus_latent=max_atk_latents)
        result.sub_damage_with_atk_latent = result.main_damage_with_atk_latent * sub_attr_multiplier
        result.total_damage_with_atk_latent = result.main_damage_with_atk_latent + result.sub_damage_with_atk_latent
        if slb_level is None:
            result.main_damage_with_slb_atk_latent = None
            result.sub_damage_with_slb_atk_latent = None
            result.total_damage_with_slb_atk_latent = None
        else:
            result.main_damage_with_slb_atk_latent = self._calculate_damage(
                dgcog, monster_model, slb_level, num_atkplus2_latent=max_atk_latents)
            result.sub_damage_with_slb_atk_latent = result.main_damage_with_slb_atk_latent * sub_attr_multiplier
            result.total_damage_with_slb_atk_latent = (result.main_damage_with_slb_atk_latent
                                                        + result.sub_damage_with_slb_atk_latent)
        result.card_btn_str = self._get_card_btn_damage(CARD_BUTTONS, dgcog, monster_model)
        result.team_btn_str = self._get_team_btn_damage(TEAM_BUTTONS, dgcog, monster_model)
        return result

    def _calculate_damage(self, dgcog, monster_model, level, num_atkplus_latent=0, num_atkplus2_latent=0):
        stat_latents = dgcog.MonsterStatModifierInput(num_atkplus=num_atkplus_latent, num_atkplus2=num_atkplus2_latent)
        stat_latents.num_atk_awakening = len(
            [x for x in monster_model.awakenings if x.awoken_skill_id == 1])

        dmg = dgcog.monster_stats.stat(monster_model, 'atk', level,
                                       stat_latents=stat_latents, multiplayer=True)

        return int(round(dmg))

    def _get_sub_attr_multiplier(self, monster_model):
        if monster_model.attr2.value == 6 or monster_model.attr1.value == 6:
            return 0
        if monster_model.attr2.value == monster_model.attr1.value:
            return 1 / 10
        return 1 / 3

    def to_string(self, dgcog, monster, info):
        card_btn_str = self._get_card_btn_damage(CARD_BUTTONS, dgcog, monster)
        team_btn_str = self._get_team_btn_damage(TEAM_BUTTONS, dgcog, monster)
        return INFO_STRING.format(monster.monster_id, monster.name_en, int(round(info.main_damage)), int(round(info.sub_damage)),
                                  int(round(info.total_damage)),
                                  int(round(info.main_damage_with_atk_latent)), int(
                                      round(info.sub_damage_with_atk_latent)),
                                  int(round(info.total_damage_with_atk_latent)), card_btn_str, team_btn_str)

    def _get_card_btn_damage(self, card_buttons, dgcog, monster):
        lines = []
        card_buttons.sort(key=lambda x: x.mult)
        for card in card_buttons:
            inherit_model = dgcog.get_monster(card.id, server=monster.server_priority)
            max_level = LIMIT_BREAK_LEVEL if monster.limit_mult != 0 else monster.level
            inherit_max_level = LIMIT_BREAK_LEVEL if inherit_model.limit_mult != 0 else inherit_model.level
            stat_latents = dgcog.MonsterStatModifierInput(num_atkplus=monster.latent_slots / 2)
            dmg = int(round(dgcog.monster_stats.stat(monster, 'atk', max_level, stat_latents=stat_latents,
                      inherited_monster=inherit_model, multiplayer=True, inherited_monster_lvl=inherit_max_level)))
            oncolor = '*' if monster.attr1.value == inherit_model.attr1.value or monster.attr1.name == NIL_ATT else ' '
            lines.append(CARD_BUTTON_FORMAT.format(
                card.id, card.name.format(oncolor), card.mult, round(dmg * card.mult, 2)))
        return "\n".join(lines)

    def _get_team_btn_damage(self, team_buttons, dgcog, monster):
        lines = []
        team_buttons.sort(key=lambda x: x.mult)
        for card in team_buttons:
            total_dmg = 0
            inherit_model = dgcog.get_monster(card.id, server=monster.server_priority)
            max_level = LIMIT_BREAK_LEVEL if monster.limit_mult != 0 else monster.level
            inherit_max_level = LIMIT_BREAK_LEVEL if inherit_model.limit_mult != 0 else inherit_model.level
            stat_latents = dgcog.MonsterStatModifierInput(num_atkplus=monster.latent_slots / 2)
            dmg = dgcog.monster_stats.stat(monster, 'atk', max_level, stat_latents=stat_latents,
                                           inherited_monster=inherit_model, multiplayer=True, inherited_monster_lvl=inherit_max_level)
            if(monster.attr1.value in card.att):
                total_dmg += dmg
            if(monster.attr2.value in card.att):
                total_dmg += dmg * self._get_sub_attr_multiplier(monster)
            colors_str = ""
            for i in card.att:
                colors_str += COLORS[i]
            oncolor = '*' if monster.attr1.value == inherit_model.attr1.value or monster.attr1.name == NIL_ATT else ' '
            lines.append(TEAM_BUTTON_FORMAT.format(card.id, card.name.format(oncolor),
                         card.mult, colors_str, round(total_dmg * card.mult, 2)))
        return "\n".join(lines)


class ButtonInfoResult:
    main_damage: float
    total_damage: float
    sub_damage: float
    main_slb_damage: float
    total_slb_damage: float
    sub_slb_damage: float
    main_damage_with_atk_latent: float
    total_damage_with_atk_latent: float
    sub_damage_with_atk_latent: float
    main_damage_with_slb_atk_latent: float
    total_damage_with_slb_atk_latent: float
    sub_damage_with_slb_atk_latent: float


button_info = ButtonInfo()
