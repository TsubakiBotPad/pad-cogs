import logging
import re
import discord


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
    'blind': "⚫",
    'super_blind': "😎",
    'to': "➡"
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
    'jammer': "🗑️🌧"
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
    'unknown': "❓"
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

def process_enemy_skill(effect: str):
    ret = ""
    split = effect.split(" + ")
    for s in split:
        n = s.split(", Deal")[0]
        temp = ""
        if "Bind" in n: ret += basic_bind(n)
        elif "Blind" in n: ret += blind(n)
        elif "skyfall" in n: ret += skyfall(n)
        elif "Change" in n and "orb" in n: ret += change_orbs_regular(n)
        elif "Increase damage" in n: ret += enemy_attack_increase(n)
        elif "Reduce damage" in n: ret += enemy_reduce_damage(n)
        elif "Voids status ailments" in n: ret += status_shield(n)
        elif "Absorb damage when" in n: ret += absorb_damage_combo(n)
        elif re.match("Absorb (.*) damage for (.*) turns?", effect): ret += absorb_attribute(n)
        elif "Void damage" in n: ret += void_damage(n)
        elif "Survive attacks with" in n: ret += resolve(n)
        elif "recover" in n: ret += recover(n)

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
            return "({}{}{})".format(generic_symbols["bind"], attribute_type_dict[bind_non_target.group(1).lower()], bind_non_target.group(2))
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
    blind_skyfall = re.match("For (.*) turns?, (.*)% chance for skyfall orbs to be blinded for (.*) turns?", effect)
    if blind_specific:
        return "({}for{})".format(generic_symbols["super_blind"], blind_specific.group(2))
    if blind_random:
        return "({}{} for {})".format(generic_symbols["super_blind"], blind_random.group(1), blind_random.group(2))
    if blind_skyfall:
        return "({}{}{}% for {})".format(skyfall_symbols["super_blind"], blind_skyfall.group(1), blind_skyfall.group(2), blind_skyfall.group(3))
    if "blind" in effect:
        return generic_symbols["blind"]
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
    change_all = re.match("Change all (.*) orbs? to (.*)", effect)
    change_random_types = re.match("Change (.*) random orb types? to (.*) orbs", effect)
    change_random_orbs = re.match("Change (.*) random orbs? to (.*) orbs", effect)

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
        g2 = multiple_cull((change_all.group(2)))
        g2_types = ""
        for g in g2:
            g2_types += attribute_type_dict[g]
        return "({}Types{}{})".format(change_random_types.group(1), generic_symbols['to'], g2_types)
    if change_random_orbs:
        g2 = multiple_cull((change_all.group(2)))
        g2_types = ""
        for g in g2:
            g2_types += attribute_type_dict[g]
        return "({}Orbs{}{})".format(change_random_types.group(1), generic_symbols['to'], g2_types)
    return ""
"""
A bunch of simple skills:

"""
def simple_cases(effect: str):
    return

"""
ESColumnSpawnMulti,
    ESRowSpawnMulti,
Change {} columns to {}
Change {} rows to {}
"""
def change_orbs_rows_cols():
    return "TODO :^)"

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
checks for the following case:
item1, Item2, and itEM3 x-> [item1, item2, item3 x]
"""
def multiple_cull(m: str):
    individuals = []
    # print(m)
    if "and" in m:
        if "," in m:
            split = m.split(", ")
            for s in split:
                if 'and' in s:
                    individuals.append(s.split('and ')[1].lower())
                else:
                    individuals.append(s.lower())
        else:
            split = m.split(" and ")
            individuals.append(split[0].lower())
            individuals.append(split[1].lower())
            return individuals
    else:
        individuals.append(m.lower())
    return individuals


    # check if
"""
ENEMY_SKILLS = [
    
    
   
    ESDispel,
  
    
    ESJammerChangeSingle,
    ESJammerChangeRandom,

    ESAttackMultihit,
    ESInactivity16,
    ESInactivity66,
   
    
    ESDebuffMovetime,
    ESEndBattle,
    ESChangeAttribute,
    ESAttackPreemptive,

    ESGravity,
   
    ESPoisonChangeSingle,
    ESPoisonChangeRandom,
    ESPoisonChangeRandomCount,
    ESMortalPoisonChangeRandom,

    ESPoisonChangeRandomAttack,

    

    ESDeathCry,

    ESLeaderSwap,

    ESBoardChangeAttackFlat,
    ESAttackSinglehit,
    ESSkillSet,
    ESBoardChange,
    ESBoardChangeAttackBits,
    

    ESSkillDelay,
    ESRandomSpawn,
    ESNone,
    ESOrbLock,
    ESSkillSetOnDeath,

    ESOrbSealColumn,
    ESOrbSealRow,
    ESFixedStart,
    ESBombRandomSpawn,
    ESBombFixedSpawn,
    ESCloud,
    ESDebuffRCV,
    ESAttributeBlock,

    ESSpinnersRandom,
    ESSpinnersFixed,
    ESMaxHPChange,
    ESFixedTarget,
    ESInvulnerableOn,
    ESInvulnerableOnHexazeon,
    ESInvulnerableOff,
    ESGachaFever,
    ESLeaderAlter,
    ESBoardSizeChange,

    ESFlagOperation,
    ESBranchFlag0,
    ESSetCounter,
    ESBranchHP,
    ESBranchCounter,
    ESBranchLevel,
    ESBranchDamageAttribute,
    ESBranchSkillUse,
    ESBranchDamage,
    ESBranchEraseAttr,
    ESEndPath,
    ESCountdown,
    ESSetCounterIf,
    ESBranchFlag,
    ESPreemptive,
    ESBranchCard,
    ESBranchCombo,
    ESBranchRemainingEnemies,

    ESTurnChangePassive,
    ESTurnChangeRemainingEnemies,
    ESTypeResist,
    ESDebuffATK,
    ESSuperResolve,
   
]
"""