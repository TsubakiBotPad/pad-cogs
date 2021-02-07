import logging
import re
from typing import List

import discord

from dungeon.grouped_skillls import GroupedSkills
from dungeon.models.EnemySkill import EnemySkill

TARGET_NAMES = [
    '<targets unset>',
    # Specific Subs
    'random card',
    'player leader',
    'both leaders',
    'friend leader',
    'random sub',
    'attributes',
    'type',
    'card',
    # Specific Players/Enemies (For Recovery)
    'player',
    'enemy',
    'enemy ally',
    # Full Team Aspect
    'awoken skills',
    'active skills',
]

generic_symbols = {
    'bind': "❌",
    'blind': "😎",
    'super_blind': "😎😎",
    'to': "➡",
    'attack': '🤜',
    'multi_attack': '🤜🤜',
    'self': '👹',
    'health': '❤',
}

skyfall_symbols = {
    'super_blind': "😎🌧️",
    'no': "🛑🌧",
    'fire': "🔥🌧",
    'water': "🌊🌧",
    'wood': "🌿🌧",
    'dark': "🌙🌧",
    'light': "💡🌧",
    'heal': "🩹🌧",
    'poison': "☠🌧",
    'mortal poison': "☠☠🌧",
    'jammer': "🗑️🌧",
    'locked fire': "🔒🔥🌧",
    'locked water': "🔒🌊🌧",
    'locked wood': "🔒🌿🌧",
    'locked dark': "🔒🌙🌧",
    'locked light': "🔒💡🌧",
    'locked heal': "🔒🩹🌧",
    'locked poison': "🔒☠🌧",
    'locked mortal poison': "🔒☠☠🌧",
    'locked jammer': "🔒🗑️🌧",
    'locked bomb': '🔒💣🌧',
    'locked random': '🔒Random🌧'
}

skills_dict = {
    'awoken': "👁️",
    'active': "🪄",
    'recover': "🏥",
    'roulette': "🎰",
}

attribute_type_dict = {
    'dragon': "🐉",
    'balanced': "⚖",
    'physical': "🛡️",
    'healer': "❤",
    'attacker': "⚔",
    'god': "😇",
    'devil': "😈",
    'machine': "⚙",
    'fire': "🔥",
    'water': "🌊",
    'wood': "🌿",
    'dark': "🌙",
    'light': "💡",
    'heal': "🩹",
    'poison': "☠",
    'mortal poison': "☠☠",
    'jammer': "🗑️",
    'locked fire': "🔒🔥",
    'locked water': "🔒🌊",
    'locked wood': "🔒🌿",
    'locked dark': "🔒🌙",
    'locked light': "🔒💡",
    'locked heal': "🔒🩹",
    'locked poison': "🔒☠",
    'locked mortal poison': "🔒☠☠",
    'locked jammer': "🔒🗑️",
    'locked bomb': '🔒💣',
    'locked random': '🔒Random',
    'bomb': '💣',
    'unknown': "❓",
    'blocked fire': "🚫🔥",
    'blocked water': "🚫🌊",
    'blocked wood': "🚫🌿",
    'blocked dark': "🚫🌙",
    'blocked light': "🚫💡",
    'blocked heal': "🚫🩹",
    'blocked poison': "🚫☠",
    'blocked mortal poison': "🚫☠☠",
    'blocked jammer': "🚫🗑️",
    'blocked bomb': '🚫💣',
    'blocked random': '🚫Random',
}

status_emoji = {
    'attack': "🗡️",
    'defense': "🛡️",
    'defense25': "🛡️25%",
    'defense50': "🛡️50%",
    'defense75': "🛡️75%",
    'defense80': "🛡️80%",
    'defense90': "🛡️90%",
    'defense95': "🛡️95%",
    'defense99': "🛡️99%",
    'combo': "🌪️",
    'absorb': "🌪️",
    'damage_absorb': "🗡️🌪️",
    'void': "🧱",
    'status_shield': "🛡️Status",
    'fire_absorb': "🔥🌪️",
    'water_absorb': "🌊🌪️",
    'wood_absorb': "🌿🌪️",
    'dark_absorb': "🌙🌪️",
    'light_absorb': "💡🌪️",
    'resolve': "👌",
    'rcv_buff': "🩹⬆️",
    'atk_debuff': "🗡️⬇️",
    'rcv_debuff': "🩹⬇️",
    'time_buff': "☝⬆",
    'time_debuff': "☝⬇",
    'roulette': "🎰",
    'dispel': "(Dispel)",
    'swap': "♔🔀",
    'skill_delay': '🔋',
    'locked': '🔒',
    'tape': '🧻',
    'starting_position': '☝🎯',
    'cloud': '☁',
    'gravity': '💔',
    'invincible': '🛡️🛡️🛡️',
    'invincible_off': '🛡️🛡️🛡️❌',
    'force_target': '🎯',
    'leader_alter': '♔➡',
    'board_size': '🌎',
    'super_resolve': '👌👌',
    'turn_change': '⌛'
}

special_hazard = {
    1: 'bind',
    2: 'awoken bind',
    3: 'delay',
    4: 'time reduction',
    5: 'atk debuff',
    6: 'rcv debuff',
    7: 'blind',
    8: 'poison',
    9: 'jammer',
    10: 'damage null',
    11: 'lock',
    12: 'roulette',
    13: 'cloud',
    14: 'tape',
    15: 'lock',
    16: 'leader swap',
    17: 'leader transform',
    18: 'no match',
    19: 'blind skyfall',
    20: 'poison skyfall',
    21: 'jammer skyfall',
    22: 'lock skyfall'
}

"""
def bind(self, min_turns, max_turns, target_count=None, target_types=TargetType.card, source: Source = None):
        if isinstance(target_types, TargetType):
            target_types = [target_types]
        elif source is not None:
            target_types = SOURCE_FUNCS[source]([target_types]) + ' cards'
        targets = targets_to_str(target_types)
        output = 'Bind {:s} '.format(pluralize2(targets, target_count))
        output += 'for ' + pluralize2('turn', minmax(min_turns, max_turns))
        return output
"""


def pluralize2_reverse(exp: str):
    return


def minmax_reverse(exp: str):
    return


def read_bind(effect: str):
    "Bind (either noun or number(num or num~num2 noun(s)) for number (or num~num2) turn(s)"
    m = re.match("Bind (.*) for (.*) turns?")
    return


def check_multi(effect: str):
    splits = str.split(" + ")


def process_enemy_skill(effect: str, encounter: dict, skill: dict):
    atk = encounter['atk']
    ret = ""
    split = effect.split(" + ")
    hazards = []
    for s in split:
        effect = ""
        n = s.split(", Deal")[0]
        # print(n)
        if "Bind" in n:
            effect += basic_bind(n)
        elif ("Blind" in n) or ("blinded" in n):
            effect += blind(n)
        elif "skyfall" in n:
            effect += skyfall(n)
        elif "Change" in n and ("orb" in n or "orbs" in n):
            effect += change_orbs_regular(n)
        elif "Increase damage" in n:
            effect += enemy_attack_increase(n)
        elif "Reduce damage" in n:
            effect += enemy_reduce_damage(n)
        elif "Voids status ailments" in n:
            effect += status_shield(n)
        elif "Absorb damage when" in n:
            effect += absorb_damage_combo(n)
        elif re.match("Absorb (.*) damage for (.*) turns?", n):
            effect += absorb_attribute(n)
        elif "Void damage" in n:
            effect += void_damage(n)
        elif "Survive attacks with" in n:
            effect += resolve(n)
        elif "recover" in n:
            effect += recover(n)
        elif "Spawn" in n:
            effect += spawn_orb(n)
        elif "Do nothing" in n:
            effect += "💤"
        elif "ATK" in n or "RCV" in n:
            effect += rcv_atk_debuff(n)
        elif "Movetime" in n:
            effect += movetime(n)
        elif "orbs change every" in n:
            effect += hells_casino(n)
        elif "Change own attribute" in n:
            effect += change_attribute(n)
        elif "Voids player buff effects" in n:
            effect += status_emoji['dispel']
        elif re.match("Player -(.*)% HP", n):
            effect += gravity(n)
        elif "Leader changes to random sub" in n:
            effect += leader_swap(n)
        elif "Delay active skills" in n:
            effect += delay_skills(n)
        elif "Lock" in n:
            effect += orb_lock(n)
        elif "Seal the" in n:
            effect += tape(n)
        elif "Fix orb movement starting point to random position on the board" in n:
            effect += status_emoji['starting_position']
        elif "clouds" in n:
            effect += clouds(n)
        elif "Change player HP to" in n:
            effect += change_player_hp(n)
        elif "Remove damage immunity" in n:
            effect += remove_damage_immune(n)
        elif "Immune to damage from all sources" in n:
            effect += damage_immune(n)
        elif "Forces attacks to hit" in n:
            effect += force_target(n)
        elif "Change leader to" in n:
            effect += leader_alter(n)
        elif "Change board size to" in n:
            effect += board_size(n)
        elif "Unable to match" in n:
            effect += unable_to_match(n)
        elif "Damage which would reduce HP from above" in n:
            effect += super_resolve(n)
        elif 'Enemy turn counter change' in n:
            effect += turn_change(n)
        if len(effect) == 0:
            reg = re.match("(.*)Deal (.*) damage", s)
            if reg:
                if len(reg.group(1)) != 0 and "Deal" not in reg.group(1):
                    effect = "(Not Processed)"
            else:
                effect = "(Not Processed)"
        ret += effect
    if skill['min_hits'] != 0:
        emoji = generic_symbols['attack']
        if skill['min_hits'] > 1:
            emoji = generic_symbols['multi_attack']
        damage_per_hit = (int)(atk * (skill['atk_mult'] / 100.0))
        min_damage = skill['min_hits'] * damage_per_hit
        max_damage = skill['max_hits'] * damage_per_hit
        if min_damage != max_damage:
            ret += "({}:{}~{})".format(emoji, f'{min_damage:,}', f'{max_damage:,}')
        else:
            ret += "({}:{})".format(emoji, f'{min_damage:,}')

    return ret


"""
ESBindRandom, "Bind {} random card for {}~{} turns"     y
ESBindAttribute, "Bind {attribute} cards for {} turns   y
ESBindTyping, Bind {type} cards for {} turns    y
 ESBindSkill, Bind active skills for {} turns   y
 ESBindTarget, Bind {target} for {} turns, specifically check for friend leaders/leader
 ESBindAttack, Any of the other binds, damage
  ESBindRandomSub, Bind {} random subs or {} turns
  ESBindAwoken, Bind awoken skills for {} turns     y
"""


def basic_bind(effect: str):
    bind_non_target = re.match("Bind (.*) cards? for (.*) turns?", effect)
    bind_skills = re.match("Bind (.*) skills for (.*) turns?", effect)
    bind_target = re.match("Bind (.*) for (.*) turns", effect)
    if bind_skills:
        return "(" + generic_symbols["bind"] + skills_dict[bind_skills.group(1)] + bind_skills.group(2) + ")"

    if bind_non_target:
        if any(bind_non_target.group(1).lower() in s for s in attribute_type_dict.keys()):
            return "({}{}{})".format(generic_symbols["bind"], attribute_type_dict[bind_non_target.group(1).lower()],
                                     bind_non_target.group(2))
        if "random" in bind_non_target.group(1):
            return "({}random{})".format(generic_symbols["bind"], bind_non_target.group(2))

    if bind_target:
        if "friend" in bind_target.group(1):
            return "({}Friend{})".format(generic_symbols["bind"], bind_non_target.group(2))
        if "both" in bind_target.group(1):
            return "({}Both{})".format(generic_symbols["bind"], bind_non_target.group(2))
        if "leader" in bind_target.group(1):
            return "({}Your Leader{})".format(generic_symbols["bind"], bind_non_target.group(2))

    if "Bind" in effect:
        return generic_symbols["bind"]
    return ""


"""
 ESBlind5,
    ESBlind62,
    ESBlindStickyRandom,
    ESBlindStickyFixed,
    ESBlindStickySkyfall, For 1 turn, 30% chance for skyfall orbs to be blinded for turn, Deal 100% damage
"""


def blind(effect: str):
    blind_specific = re.match("Blind orbs in specific positions for (.*) turns?", effect)
    blind_random = re.match("Blind random (.*) orbs for (.*) turns?", effect)
    blind_skyfall = re.match("For (.*) turns?, (.*)% chance for skyfall orbs to be blinded for", effect)
    if blind_specific:
        return "({}for{})".format(generic_symbols["super_blind"], blind_specific.group(1))
    if blind_random:
        return "({}{} for {})".format(generic_symbols["super_blind"], blind_random.group(1), blind_random.group(2))
    if blind_skyfall:
        return "({}{}% for {})".format(skyfall_symbols["super_blind"], blind_skyfall.group(2),
                                       blind_skyfall.group(1))
    if "Blind all orbs" in effect:
        return "({}All)".format(generic_symbols["blind"])
    return ""


"""

    ESSkyfall, Fire, Water, Wood, Light, and Dark skyfall +100% for 1 turn
    ESSkyfallLocked,
        ESNoSkyfall,
    ESComboSkyfall,
"""


def skyfall(effect: str):
    # multiple_case = re.match("(.*) and (.*) skyfall (.*) for (.*) turns?", effect)
    regular_case = re.match("(.*) skyfall (.*) for (.*) turns?", effect)
    no_case = re.match("No skyfall for (.*) turns?", effect)
    # need to check comboskyfall also
    if no_case:
        return "({}{})".format(skyfall_symbols['no'], no_case.group(1))
    if regular_case:
        types = ""
        if "Locked" in regular_case.group(1):
            for a in multiple_cull(regular_case.group(1).replace("Locked ", '')):
                types += skyfall_symbols["locked {}".format(a)]
        else:
            for s in multiple_cull(regular_case.group(1)):
                types += skyfall_symbols[s]
        return "({}{} for {})".format(types, regular_case.group(2), regular_case.group(3))
    return ""


"""
    ESOrbChangeAttackBits,
        ESOrbChangeSingle,
    ESOrbChangeAttack,
Skills that are of: 
Change all {} orbs? to {}
Change {} random orbs? to {}
Change {} random orb types? to {}

top generic: Change {} to {}
output: 
"""


def change_orbs_regular(effect: str):
    if "column" in effect:
        return change_column_row(effect)
    elif "row" in effect:
        return change_column_row(effect, row=True)
    actually_change_all = re.match("Change all orbs to (.*)", effect)
    change_all = re.match("Change all (.*) orbs? to (.*)", effect)
    change_random_types = re.match("Change (.*) random orb types? to (.*) orbs", effect)
    change_random_orbs = re.match("Change (.*) random orbs? to (.*) orbs", effect)
    change_a_random_att = re.match("Change a random attribute to (.*) orbs", effect)
    if change_a_random_att:
        types = multiple_cull(change_a_random_att.group(1))
        emoji = ""
        for t in types:
            emoji += attribute_type_dict[t]
        return "(Random Att{}{})".format(generic_symbols['to'], emoji)
    if actually_change_all:
        types = multiple_cull(actually_change_all.group(1))
        emoji = ""
        for t in types:
            emoji += attribute_type_dict[t]
        return "(All{}{})".format(generic_symbols['to'], emoji)
    if change_all:
        g1 = multiple_cull(change_all.group(1))
        g1_types = ""
        g2 = multiple_cull(change_all.group(2).split(" orbs")[0])
        g2_types = ""
        for g in g1:
            g1_types += attribute_type_dict[g]
        if len(g1) == 0:
            g1_types = "All"
        for g in g2:
            g2_types += attribute_type_dict[g]
        return "({}{}{})".format(g1_types, generic_symbols['to'], g2_types)
    if change_random_types:
        g2 = multiple_cull((change_random_types.group(2)))
        g2_types = ""
        for g in g2:
            g2_types += attribute_type_dict[g]
        return "({}Types{}{})".format(change_random_types.group(1), generic_symbols['to'], g2_types)
    if change_random_orbs:
        g2 = multiple_cull((change_random_orbs.group(2)))
        g2_types = ""
        for g in g2:
            g2_types += attribute_type_dict[g]
        return "({}Orbs{}{})".format(change_random_orbs.group(1), generic_symbols['to'], g2_types)
    return ""


"""
A bunch of simple skills:

"""


def simple_cases(effect: str):
    return


"""
ESColumnSpawnMulti,
    ESRowSpawnMulti,
Change the 2nd column to Fire orbs and the 4th column to Fire orbs
Change {} rows to {}
"""


def change_column_row(effect: str, row: bool = False):
    column = re.match("Change the (.*) columns? to (.*) orbs?", effect)
    column_multi = re.match("Change the (.*) columns? to (.*) orbs? and the (.*) columns? to (.*) orbs?", effect)
    if row:
        column = re.match("Change the (.*) rows? to (.*) orbs?", effect)
        column_multi = re.match("Change the (.*) rows? to (.*) orbs? and the (.*) rows? to (.*) orbs?", effect)
    if column_multi:
        orb_cull = multiple_cull(column_multi.group(2))
        emoji = ""
        ret = ""
        for o in orb_cull:
            emoji += attribute_type_dict[o]
        if not row:
            ret += "(Columns: {}{}{})".format(column_multi.group(1), generic_symbols['to'], emoji)
        else:
            ret += "(Rows: {}{}{})".format(column_multi.group(1), generic_symbols['to'], emoji)
        orb_cull = multiple_cull(column_multi.group(4))
        emoji = ""
        for o in orb_cull:
            emoji += attribute_type_dict[o]
        if not row:
            ret += "(Columns: {}{}{})".format(column_multi.group(3), generic_symbols['to'], emoji)
        else:
            ret += "(Rows: {}{}{})".format(column_multi.group(3), generic_symbols['to'], emoji)
        return ret
    elif column:
        orb_cull = multiple_cull(column.group(2))
        emoji = ""
        ret = ""
        for o in orb_cull:
            emoji += attribute_type_dict[o]
        if not row:
            ret += "(Columns: {}{}{})".format(column.group(1), generic_symbols['to'], emoji)
        else:
            ret += "(Rows: {}{}{})".format(column.group(1), generic_symbols['to'], emoji)
        return ret
    return ""


"""

    ,
    ESStorePower,
   
      
     
          
    
        ESAttributeResist,
    
"""


def enemy_status():
    return


"""
 ESAttackUPRemainingEnemies,
    ESAttackUpStatus,
    ESAttackUPCooldown,
    Increase damage to 150% for the next 999 turns
"""


def enemy_attack_increase(effect: str):
    increase = re.match("Increase damage to (.*) for the next (.*) turns?", effect)
    if increase:
        return "({}+{} for {})".format(status_emoji['attack'], increase.group(1), increase.group(2))
    return ""


"""
ESDamageShield,
Reduce damage from {source} by {amount} {for {} turns}
"""


def enemy_reduce_damage(effect: str):
    shield = re.match("Reduce damage from all sources by (.*)% for (.*) turns?", effect)
    passive = re.match("Reduce damage from (.*) by (.*)", effect)
    if shield:
        try:
            emoji = status_emoji["defense" + shield.group(1)]
        except KeyError:
            emoji = status_emoji["defense"] + shield.group(1) + "%"
        return "({} for {})".format(emoji, shield.group(2))
    if passive:
        # print(effect)
        atts = multiple_cull(passive.group(1))
        emoji = ""
        for a in atts:
            if " attrs" in a:
                emoji += attribute_type_dict[a.split(' attrs')[0]]
            elif " types" in a:
                emoji += attribute_type_dict[a.split(' types')[0]]
            else:
                emoji += attribute_type_dict[a]
        return "({}-{})".format(emoji, passive.group(2))
    return ""


"""
ESStatusShield
Voids status ailments for {number} turns
"""


def status_shield(effect: str):
    status = re.match("Voids status ailments for (.*) turns?", effect)
    if status:
        return "({} for {})".format(status_emoji['status_shield'], status.group(1))
    return ""


"""
 ESAbsorbCombo,
  ESAbsorbThreshold,
  Absorb damage when {combo, damage} {threshold} for {number} turns
"""


def absorb_damage_combo(effect: str):
    absorb = re.match("Absorb damage when (.*) (.*) (.*) for (.*) turns?", effect)
    if absorb:
        if "combo" in absorb.group(1):
            try:
                emoji = status_emoji["combo" + absorb.group(3)]
            except KeyError:
                emoji = "{} Combo{}".format(absorb.group(3), status_emoji['combo'])
            return "({} for {})".format(emoji, absorb.group(4))
        else:
            return "({}{} for {})".format(status_emoji['damage_absorb'], absorb.group(3), absorb.group(4))
    return ""


"""
ESAbsorbAttribute,
Absorb {Fire, Water, and Wood} damage for 5 turns
"""


def absorb_attribute(effect: str):
    absorb = re.match("Absorb (.*) damage for (.*) turns?", effect)
    if absorb:
        atts = multiple_cull(absorb.group(1))
        emoji = ""
        for a in atts:
            emoji += status_emoji["{}_absorb".format(a)]
        return "({} for {})".format(emoji, absorb.group(2))
    return ""


"""
ESVoidShield,
Void damage >= {1,000,000} for {2} turns?
"""


def void_damage(effect: str):
    void = re.match("Void damage >= (.*) for (.*) turns?", effect)
    if void:
        return "({}{} for {})".format(status_emoji['void'], void.group(1), void.group(2))
    return ""


"""
ESResolve,
Survive attacks with {1} HP when HP > {50}%
"""


def resolve(effect: str):
    resolve = re.match("Survive attacks with (.*) HP when HP > (.*)", effect)
    if resolve:
        return "({}{})".format(status_emoji['resolve'], resolve.group(2))
    return ""


"""
  ESRecoverEnemy7,
    ESRecoverEnemy86,
     ESRecoverEnemyAlly,
    ESRecoverPlayer,
{Player, Enemy, Enemy ally} recover {%10} HP
"""


def recover(effect: str):
    recover = re.match("(.*) recover (.*) HP", effect)
    if recover:
        return "({}{}{}{})".format(skills_dict['recover'], recover.group(2), generic_symbols['to'], recover.group(1))
    return ""


"""
    ESJammerChangeSingle,
    ESJammerChangeRandom,
      ESPoisonChangeSingle,
    ESPoisonChangeRandom,
    ESPoisonChangeRandomCount,
    ESMortalPoisonChangeRandom,

    ESPoisonChangeRandomAttack,
       ESBombRandomSpawn,
    ESBombFixedSpawn,
    
    Spawn {number} random {bomb, jammer, poison, mortal poison} orbs
    Spawn {bomb, jammer, poison, mortal poison} orbs in the specified positions
"""


def spawn_orb(effect: str):
    spawn = re.match("Spawn (.*) random (.*) orbs?", effect)
    specified = re.match("Spawn (.*) orbs in the specified positions?", effect)
    if spawn:
        atts = multiple_cull(spawn.group(2))
        emoji = ""
        for a in atts:
            emoji += attribute_type_dict[a]
        return "({}{})".format(emoji, spawn.group(2))
    if specified:
        atts = multiple_cull(specified.group(1))
        emoji = ""
        for a in atts:
            emoji += attribute_type_dict[a]
        return "({})".format(emoji)
    return ""


"""
RCV and ATK Debuff
{ATK, RCV} {amount} for 1 turn
"""


def rcv_atk_debuff(effect: str):
    debuff = re.match("(.*) (.*)% for (.*) turns?", effect)
    if debuff:
        emoji = ""
        if "RCV" in debuff.group(1):
            if int(debuff.group(2)) >= 100:
                emoji += status_emoji['rcv_buff']
            else:
                emoji += status_emoji['rcv_debuff']
        elif "ATK" in debuff.group(1):
            emoji += status_emoji['atk_debuff']
        return "({}{}% for {})".format(emoji, debuff.group(2), debuff.group(3))
    return ""


"""
Movetime Debuff/Buff
Movetime {amount} for {turns} turns?
"""


def movetime(effect: str):
    fingers = re.match("Movetime (.*) for (.*) turns?", effect)
    if fingers:
        emoji = status_emoji['time_debuff']
        if "%" in fingers.group(1):
            if int(fingers.group(1).replace('%', '')) >= 100:
                emoji = status_emoji['time_buff']
        return "({}{} for {})".format(emoji, fingers.group(1), fingers.group(2))
    return ""


"""
Roulette, Spinners, Hell
Specific orbs change every {1.0}s for {10} turns 
"""


def hells_casino(effect: str):
    speen = re.match("Specific orbs change every (.*) for (.*) turns?", effect)
    speen2 = re.match("Random (.*) orbs change every (.*) for (.*) turns?", effect)
    if speen:
        return "({}{} for {})".format(status_emoji['roulette'], speen.group(1), speen.group(2))
    if speen2:
        return "({}{}Random {} for {})".format(status_emoji['roulette'], speen2.group(2), speen2.group(1),
                                               speen2.group(3))
    return ""


"""
Change Attribute
Change own attribute to {att}
"""


def change_attribute(effect: str):
    change = re.match("Change own attribute to (.*)", effect)
    change_random = re.match("Change own attribute to random one of (.*)", effect)
    if change_random:
        emoji = ""
        atts = multiple_cull(change_random.group(1), 'or')
        for a in atts:
            emoji += attribute_type_dict[a]
        return "({}{}{})".format(generic_symbols['self'], generic_symbols['to'], emoji)
    if change:
        return "({}{}{})".format(generic_symbols['self'], generic_symbols['to'],
                                 attribute_type_dict[change.group(1).lower()])
    return ""


"""
Gravity
Player {-99%} HP
"""


def gravity(effect: str):
    hit = re.match("Player -(.*)% HP", effect)
    if hit:
        return "(-{}%{})".format(hit.group(1), status_emoji['gravity'])
    return ""


"""
Leader Swap
Leader changes to random sub for {1} turn
"""


def leader_swap(effect: str):
    swap = re.match("Leader changes to random sub for (.*) turns?", effect)
    if swap:
        return "({} for {})".format(status_emoji['swap'], swap.group(1))
    return ""


"""
Skill Delay
Delay active skills by {3} turns?
"""


def delay_skills(effect: str):
    delay = re.match("Delay active skills by (.*) turns?", effect)
    if delay:
        return "({}-[{}])".format(status_emoji['skill_delay'], delay.group(1))
    return ""


"""
Orb Lock
Lock {number random/all} {atts or not specified} orbs
"""


def orb_lock(effect: str):
    '''lock = re.match("Lock (.*) (.*) orbs?", effect)
    lock_no_atts = re.match("Lock (.*) orbs?", effect)
    if lock:
        number = "All"
        orb_emojis = ""
        if "random" in lock.group(1):
            number = lock.group(1).strip(" random")
        if lock:
            atts = multiple_cull(lock.group(2))
            for a in atts:
                orb_emojis += attribute_type_dict[a]
        return "({}{}:{})".format(status_emoji['locked'], number, orb_emojis)
    elif lock_no_atts:
        number = "All"
        if "random" in lock_no_atts.group(1):
            number = lock_no_atts.group(1).strip(" random")
        return "({}{})".format(status_emoji['locked'], number)'''
    lock_random_no_atts = re.match("Lock (.*) random orbs?", effect)
    lock_random = re.match("Lock (.*) random (.*) orbs?", effect)
    lock_all_atts = re.match("Lock all (.*) orbs?", effect)

    if "Lock all orbs" in effect:
        return "({}All)".format(status_emoji['locked'])
    if lock_random_no_atts:
        return "({}{})".format(status_emoji['locked'], lock_random_no_atts.group(1))
    if lock_random:
        number = lock_random.group(1)
        emoji = ""
        atts = multiple_cull(lock_random.group(2))
        for a in atts:
            emoji += attribute_type_dict[a]
        return "({}{}:{})".format(status_emoji['locked'], number, emoji)
    if lock_all_atts:
        emoji = ""
        atts = multiple_cull(lock_all_atts.group(1))
        for a in atts:
            emoji += attribute_type_dict[a]
        return "({}All:{})".format(status_emoji['locked'], emoji)
    return ""


"""
Seal Orbs (Tape)
Seal the {1st and 2nd} columns? for {2} turns?
Seal the {1st and 2nd} rows? for {2} turns? 
"""


def tape(effect: str):
    tape = re.match("Seal the (.*) (.*) for (.*) turns?", effect)
    if tape:
        if "column" in tape.group(2):
            return "({}C:{} for {})".format(status_emoji['tape'], tape.group(1), tape.group(3))
        return "({}R:{} for {})".format(status_emoji['tape'], tape.group(1), tape.group(3))
    return ""


"""
Cloud
A {dimensions} {square, rectangle} of clouds appears for {1} turns? at {3rd row, 2nd Column/ a random position}
"""


def clouds(effect: str):
    clouds_random = re.match("A (.*) (.*) of clouds appears for (.*) turns? at a random location", effect)
    clouds_specific = re.match("A (.*) (.*) of clouds appears for (.*) turns? at (.*) row, (.*) column", effect)
    if clouds_random:
        return "({}{} for {})".format(status_emoji['cloud'], clouds_random.group(1), clouds_random.group(3))
    if clouds_specific:
        dimensions = clouds_specific.group(1)
        r = clouds_specific.group(4)
        c = clouds_specific.group(5)
        turns = clouds_specific.group(3)
        return "({}{} at [{},{}] for {})".format(status_emoji['cloud'], dimensions, r, c, turns)
    return ""


"""
Change Player HP
Change player HP to {10,000} for {8} turns?
"""


def change_player_hp(effect: str):
    change = re.match("Change player HP to (.*) for (.*) turns?", effect)
    if change:
        return "({}= {} for {})".format(generic_symbols['health'], change.group(1), change.group(2))
    return ""


"""
Immune to Damage
Immune to damage from all sources
"""


def damage_immune(effect: str):
    immune = re.match("Immune to damage from all sources", effect)
    if immune:
        return "({})".format(status_emoji['invincible'])
    return ""


"""
Remove damage immunity effect
"""


def remove_damage_immune(effect: str):
    immune = re.match("Remove damage immunity", effect)
    if immune:
        return "({})".format(status_emoji['invincible_off'])
    return ""


"""
Forces attacks to hit this enemy for {} turns
"""


def force_target(effect: str):
    force = re.match("Forces attacks to hit this enemy for (.*) turns?", effect)
    if force:
        return "({}{})".format(status_emoji['force_target'], force.group(1))
    return ""


"""
Leader Alter
Change leader to [{monster_number}] for {10} turns
"""


def leader_alter(effect: str):
    alter = re.match("Change leader to \[(.*)] for (.*) turns?", effect)
    if alter:
        return "({}{} for {})".format(status_emoji['leader_alter'], alter.group(1), alter.group(2))
    return ""


"""
Board size change
Change board size to {7x6} for {3} turns
"""


def board_size(effect: str):
    size = re.match("Change board size to (.*) for (.*) turns?", effect)
    if size:
        return "({}{} for {})".format(size.group(1), status_emoji['board_size'], size.group(2))
    return ""


"""
Unable to match {wood and light} orbs
"""


def unable_to_match(effect: str):
    unable = re.match("Unable to match (.*) orbs? for (.*) turns?", effect)
    if unable:
        orbs = multiple_cull(unable.group(1))
        emoji = ""
        for o in orbs:
            emoji += attribute_type_dict['blocked ' + o]
        return "({} for {})".format(emoji, unable.group(2))
    return ""


"""
Super resolve
Damage which would reduce HP from above (.*) to below (.*) is nullified
"""


def super_resolve(effect: str):
    sr = re.match("Damage which would reduce HP from above (.*) to below (.*) is nullified", effect)
    if sr:
        return "({}{})".format(status_emoji['super_resolve'], sr.group(1))


"""
Turn Change
Enemy turn counter change to {1} when HP <= {10%}
"""


def turn_change(effect: str):
    tc = re.match("Enemy turn counter change to (.*) when HP <= (.*)", effect)
    if tc:
        return "({}{}Now HP {})".format(status_emoji['turn_change'], generic_symbols['to'], tc.group(2))


"""
checks for the following case:
item1, Item2, and itEM3 x-> [item1, item2, item3 x]
"""


def multiple_cull(m: str, key: str = 'and'):
    individuals = []

    # print("multiple_cull: {} {}".format(m, key))
    if (key + " ") in m:
        if "," in m:
            split = m.split(", ")
            for s in split:
                if key in s:
                    individuals.append(s.split('{} '.format(key))[1].lower())
                else:
                    individuals.append(s.lower())
        else:
            split = m.split(" {} ".format(key))
            individuals.append(split[0].lower())
            individuals.append(split[1].lower())
            return individuals
    else:
        individuals.append(m.lower())
    return individuals


class ProcessedSkill(object):
    def __init__(self, name: str, effect: str, processed: str, condition: str = None, parent: GroupedSkills = None,
                 es_raw: List[EnemySkill] = None):
        self.name = name
        self.effect = effect
        self.processed = processed
        self.condition = condition
        self.parent = parent
        self.type = self.find_type()
        self.is_passive_preempt = len(self.process_type()) != 0
        self.es_raw = es_raw

    def find_type(self):
        up = self.parent
        while up is not None:
            if up.type is not None:
                return up.type
            up = up.parent
        return None

    def process_type(self):
        if "Passive" in self.type or "Preemptive" in self.type:
            return "({})".format(self.type)
        return ""

    def give_string(self, indent: str = "", verbose: bool = False):
        if len(self.processed) == 0:
            self.processed = "(N/A)\n"
        if verbose:
            if self.condition is not None:
                ret = '''**{}{}S: {}**\n{}E: {}\n**{}Condition: {}**'''.format(indent, self.process_type(),
                                                                               self.processed, indent, self.effect,
                                                                               indent, self.condition)
                return ret
            else:
                ret = '''**{}{}S: {}**\n{}E: {}'''.format(indent, self.process_type(), self.processed, indent,
                                                          self.effect)
                return ret
        else:
            if self.condition is not None:
                ret = '''**{}{}S: {}**\n**{}Condition: {}**'''.format(indent, self.process_type(), self.processed,
                                                                      indent,
                                                                      self.condition)
                return ret
            else:
                ret = '''**{}{}S: {}**'''.format(indent, self.process_type(), self.processed)
                return ret
    # check if


"""
ENEMY_SKILLS = [
    ESEndBattle,
    ESDeathCry,
    ESNone,
    ESSkillSetOnDeath,
    ESAttributeBlock


    ESGachaFever,




    ESCountdown,
    ESSetCounterIf,



    ESTurnChangeRemainingEnemies,


   
]
"""
