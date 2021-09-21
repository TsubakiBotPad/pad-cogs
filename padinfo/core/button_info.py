from collections import namedtuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel

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

TEAM_BUTTON_FORMAT = "[{}] {} ({} {}): {}"
CARD_BUTTON_FORMAT = "[{}] {} ({}): {}"

MonsterStat = namedtuple('MonsterStat', 'name id mult att')

TEAM_BUTTONS = [
    # account for attributes when spacing
    MonsterStat("Nergi Hunter{}", 4172, 40, [2, 4]),
    MonsterStat("Oversoul{} ", 5273, 50, [0, 1, 2, 3, 4]),
    MonsterStat("Ryuno Ume{}   ", 5252, 80, [2, 4])
]
CARD_BUTTONS = [
    MonsterStat("Assassin{}     ", 5021, 200, []),
    MonsterStat("Satan{}        ", 4286, 300, []),
    MonsterStat("Durandalf Eq{} ", 4723, 300, []),
    MonsterStat("Brachydios Eq{}", 4152, 350, []),
    MonsterStat("Rajang Eq{}    ", 5530, 550, []),
    MonsterStat("Balrog{}       ", 5108, 450, [])
]

COLORS = ["R", "B", "G", "L", "D"]
NIL_ATT = 'Nil'


class ButtonInfo:
    def get_info(self, dbcog, monster):
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
        max_level = LIMIT_BREAK_LEVEL if monster.limit_mult != 0 else monster.level
        slb_level = SUPER_LIMIT_BREAK_LEVEL if monster.limit_mult != 0 else None
        max_atk_latents = monster.latent_slots / 2

        sub_attr_multiplier = self._get_sub_attr_multiplier(monster)

        result = ButtonInfoResult()
        result.main_damage = self._calculate_coop_damage(dbcog, monster, max_level)
        result.sub_damage = result.main_damage * sub_attr_multiplier
        result.total_damage = result.main_damage + result.sub_damage

        if slb_level is None:
            result.main_slb_damage = None
            result.sub_slb_damage = None
            result.total_slb_damage = None
        else:
            result.main_slb_damage = self._calculate_coop_damage(dbcog, monster, slb_level)
            result.sub_slb_damage = result.main_slb_damage * sub_attr_multiplier
            result.total_slb_damage = result.main_slb_damage + result.sub_slb_damage

        result.main_solo_damage = self._calculate_solo_damage(dbcog, monster, max_level)
        result.sub_solo_damage = result.main_solo_damage * sub_attr_multiplier
        result.total_solo_damage = result.main_solo_damage + result.sub_solo_damage

        if slb_level is None:
            result.main_solo_slb_damage = None
            result.sub_solo_slb_damage = None
            result.total_solo_slb_damage = None
        else:
            result.main_solo_slb_damage = self._calculate_solo_damage(dbcog, monster, slb_level)
            result.sub_solo_slb_damage = result.main_solo_slb_damage * sub_attr_multiplier
            result.total_solo_slb_damage = result.main_solo_slb_damage + result.sub_solo_slb_damage

        result.main_damage_with_atk_latent = self._calculate_coop_damage(
            dbcog, monster, max_level, num_atkplus_latent=max_atk_latents)
        result.sub_damage_with_atk_latent = result.main_damage_with_atk_latent * sub_attr_multiplier
        result.total_damage_with_atk_latent = result.main_damage_with_atk_latent + result.sub_damage_with_atk_latent

        if slb_level is None:
            result.main_damage_with_slb_atk_latent = None
            result.sub_damage_with_slb_atk_latent = None
            result.total_damage_with_slb_atk_latent = None
        else:
            result.main_damage_with_slb_atk_latent = self._calculate_coop_damage(
                dbcog, monster, slb_level, num_atkplus2_latent=max_atk_latents)
            result.sub_damage_with_slb_atk_latent = result.main_damage_with_slb_atk_latent * sub_attr_multiplier
            result.total_damage_with_slb_atk_latent = (result.main_damage_with_slb_atk_latent
                                                       + result.sub_damage_with_slb_atk_latent)

        result.main_solo_damage_with_atk_latent = self._calculate_solo_damage(
            dbcog, monster, max_level, num_atkplus_latent=max_atk_latents)
        result.sub_solo_damage_with_atk_latent = result.main_solo_damage_with_atk_latent * sub_attr_multiplier
        result.total_solo_damage_with_atk_latent = (result.main_solo_damage_with_atk_latent
                                                    + result.sub_solo_damage_with_atk_latent)
        if slb_level is None:
            result.main_solo_damage_with_slb_atk_latent = None
            result.sub_solo_damage_with_slb_atk_latent = None
            result.total_solo_damage_with_slb_atk_latent = None
        else:
            result.main_solo_damage_with_slb_atk_latent = self._calculate_solo_damage(
                dbcog, monster, slb_level, num_atkplus2_latent=max_atk_latents)
            result.sub_solo_damage_with_slb_atk_latent = (result.main_solo_damage_with_slb_atk_latent
                                                          * sub_attr_multiplier)
            result.total_solo_damage_with_slb_atk_latent = (result.main_solo_damage_with_slb_atk_latent
                                                            + result.sub_solo_damage_with_slb_atk_latent)

        result.card_btn_str = self._get_card_btn_damage_text(CARD_BUTTONS, dbcog, monster,
                                                             multiplayer=True, limit_break=LIMIT_BREAK_LEVEL)
        result.card_btn_solo_str = self._get_card_btn_damage_text(CARD_BUTTONS, dbcog, monster,
                                                                  multiplayer=False, limit_break=LIMIT_BREAK_LEVEL)
        result.card_btn_slb_str = self._get_card_btn_damage_text(CARD_BUTTONS, dbcog, monster,
                                                                 multiplayer=True, limit_break=SUPER_LIMIT_BREAK_LEVEL)
        result.card_btn_solo_slb_str = self._get_card_btn_damage_text(CARD_BUTTONS, dbcog, monster,
                                                                      multiplayer=False,
                                                                      limit_break=SUPER_LIMIT_BREAK_LEVEL)

        result.team_btn_str = self._get_team_btn_damage_text(TEAM_BUTTONS, dbcog, monster,
                                                             multiplayer=True, limit_break=LIMIT_BREAK_LEVEL)
        result.team_btn_solo_str = self._get_team_btn_damage_text(TEAM_BUTTONS, dbcog, monster,
                                                                  multiplayer=False, limit_break=LIMIT_BREAK_LEVEL)
        result.team_btn_slb_str = self._get_team_btn_damage_text(TEAM_BUTTONS, dbcog, monster,
                                                                 multiplayer=True, limit_break=SUPER_LIMIT_BREAK_LEVEL)
        result.team_btn_solo_slb_str = self._get_team_btn_damage_text(TEAM_BUTTONS, dbcog, monster,
                                                                      multiplayer=False,
                                                                      limit_break=SUPER_LIMIT_BREAK_LEVEL)
        return result

    def _calculate_coop_damage(self, dbcog, monster, level, num_atkplus_latent=0, num_atkplus2_latent=0):
        return self._calculate_damage(dbcog, monster, level, True, num_atkplus_latent, num_atkplus2_latent)

    def _calculate_solo_damage(self, dbcog, monster, level, num_atkplus_latent=0, num_atkplus2_latent=0):
        return self._calculate_damage(dbcog, monster, level, False, num_atkplus_latent, num_atkplus2_latent)

    @staticmethod
    def _calculate_damage(dbcog, monster, level, multiplayer, num_atkplus_latent=0, num_atkplus2_latent=0):
        stat_latents = dbcog.MonsterStatModifierInput(num_atkplus=num_atkplus_latent, num_atkplus2=num_atkplus2_latent)
        stat_latents.num_atk_awakening = len(
            [x for x in monster.awakenings if x.awoken_skill_id == 1])

        dmg = dbcog.monster_stats.stat(monster, 'atk', level,
                                       stat_latents=stat_latents, multiplayer=multiplayer)

        return int(round(dmg))

    @staticmethod
    def _get_sub_attr_multiplier(monster):
        if monster.attr2.value == 6 or monster.attr1.value == 6:
            return 0
        if monster.attr2.value == monster.attr1.value:
            return 1 / 10
        return 1 / 3

    @staticmethod
    def _get_card_btn_damage_text(card_buttons, dbcog, monster: "MonsterModel", multiplayer, limit_break):
        lines = []
        card_buttons.sort(key=lambda x: x.mult)
        for card in card_buttons:
            inherit_model = dbcog.get_monster(card.id, server=monster.server_priority)
            max_level = limit_break if monster.limit_mult != 0 else monster.level
            inherit_max_level = LIMIT_BREAK_LEVEL if inherit_model.limit_mult != 0 else inherit_model.level

            num_latent_slots = monster.latent_slots / 2
            num_atkplus = num_latent_slots
            num_atkplus2 = 0
            if limit_break == SUPER_LIMIT_BREAK_LEVEL and monster.limit_mult != 0:
                num_atkplus = 0
                num_atkplus2 = num_latent_slots

            stat_latents = dbcog.MonsterStatModifierInput(num_atkplus=num_atkplus, num_atkplus2=num_atkplus2)
            dmg = int(round(dbcog.monster_stats.stat(monster, 'atk', max_level, stat_latents=stat_latents,
                                                     inherited_monster=inherit_model, multiplayer=multiplayer,
                                                     inherited_monster_lvl=inherit_max_level)))
            oncolor = '*' if monster.attr1.value == inherit_model.attr1.value or monster.attr1.name == NIL_ATT else ' '
            lines.append(CARD_BUTTON_FORMAT.format(
                card.id, card.name.format(oncolor), card.mult, round(dmg * card.mult, 2)))
        return "\n".join(lines)

    def _get_team_btn_damage_text(self, team_buttons, dbcog, monster, multiplayer, limit_break):
        lines = []
        team_buttons.sort(key=lambda x: x.mult)
        for card in team_buttons:
            total_dmg = 0
            inherit_model = dbcog.get_monster(card.id, server=monster.server_priority)
            max_level = limit_break if monster.limit_mult != 0 else monster.level
            inherit_max_level = LIMIT_BREAK_LEVEL if inherit_model.limit_mult != 0 else inherit_model.level
            stat_latents = dbcog.MonsterStatModifierInput(num_atkplus=monster.latent_slots / 2)
            dmg = dbcog.monster_stats.stat(monster, 'atk', max_level, stat_latents=stat_latents,
                                           inherited_monster=inherit_model, multiplayer=multiplayer,
                                           inherited_monster_lvl=inherit_max_level)
            # do count null main att monster damage as if it were the main att
            if monster.attr1.value in card.att or monster.attr1.name == NIL_ATT:
                total_dmg += dmg
            # do not double-count null main att
            if monster.attr2.value in card.att and monster.attr1.name != NIL_ATT:
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
    main_solo_damage: float
    total_solo_damage: float
    sub_solo_damage: float
    main_slb_damage: float
    total_slb_damage: float
    sub_slb_damage: float
    main_solo_slb_damage: float
    total_solo_slb_damage: float
    sub_solo_slb_damage: float
    main_damage_with_atk_latent: float
    total_damage_with_atk_latent: float
    sub_damage_with_atk_latent: float
    main_solo_damage_with_atk_latent: float
    total_solo_damage_with_atk_latent: float
    sub_solo_damage_with_atk_latent: float
    main_damage_with_slb_atk_latent: float
    total_damage_with_slb_atk_latent: float
    sub_damage_with_slb_atk_latent: float
    main_solo_damage_with_slb_atk_latent: float
    total_solo_damage_with_slb_atk_latent: float
    sub_solo_damage_with_slb_atk_latent: float


button_info = ButtonInfo()
