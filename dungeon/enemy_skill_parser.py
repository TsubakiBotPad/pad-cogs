from collections import OrderedDict
from typing import List

from dungeon.EnemySkillDatabase import EnemySkillDatabase
from dungeon.models.EnemySkill import EnemySkill

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
    'locked random': '🔒Random🌧',
    'combo': 'Combo'
}

skills_dict = {
    'awoken': "👁️",
    'active': "🪄",
    'recover': "🏥",
    'roulette': "🎰",
}

emoji_dict = {
    'awoken': "👁️",
    'active': "🪄",
    'recover': "🏥",
    'roulette': "🎰",
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
    'turn_change': '⌛',
    'enrage': '🗡️⬆',
    'skill_bind': '❌🪄',
    'do_nothing': '💤',
    'awoken_bind': '❌👁️',
    'no_skyfall' : 'No🌧'
}
TargetType={
    'Unset' : -1,
    # Selective Subs
    'Random' : 0,
    'Leader' : 1,
    'Both Leaders' : 2,
    'Friend Leader' : 3,
    'Subs' : 4,
    'Attributes' : 5,
    'Types' : 6,
    'Cards' : 6.5,

    # Specific Players/Enemies
    'player' : 7,
    'enemy' : 8,
    'enemy_ally' : 9,

    # Full Team Aspect
    'awokens' : 10,
    'actives' : 11,
}
OrbShape={
    'L' : 0,
    'X' : 1,
    'Col' : 2,
    'row' : 4
}

Attributes = {
        -9: '🔒💣',
        -1: 'Random Att',
        None: '🔥',
        0: '🔥',
        1: '🌊',
        2: '🌿',
        3: '💡',
        4: '🌙',
        5: '🩹',
        6: '🗑️',
        7: '☠',
        8: '☠☠',
        9: '💣',
    }

SkyfallAttributes = {
    -9: '🔒💣🌧',
    -1: 'Random Att🌧',
    None: '🔥🌧',
    0: '🔥🌧',
    1: '🌊🌧',
    2: '🌿🌧',
    3: '💡🌧',
    4: '🌙🌧',
    5: '🩹🌧',
    6: '🗑️🌧',
    7: '☠🌧',
    8: '☠☠🌧',
    9: '💣🌧',
}

UnmatchableAttributes = {
    None : "🚫🔥",
    0 : "🚫🔥",
    1 : "🚫🌊",
    2 : "🚫🌿",
    4 : "🚫🌙",
    3 : "🚫💡",
    5 : "🚫🩹",
    6: '🚫🗑',
    7: '🚫☠',
    8: '🚫☠☠',
    9: '🚫💣',
}

LockedSkyfallAttributes = {
    -9: '🔒💣🌧',
    -1: 'Random Att🔒🌧',
    None: '🔒🔥🌧',
    0: '🔒🔥🌧',
    1: '🔒🌊🌧',
    2: '🔒🌿🌧',
    3: '🔒💡🌧',
    4: '🔒🌙🌧',
    5: '🔒🩹🌧',
    6: '🔒🗑️🌧',
    7: '🔒☠🌧',
    8: '🔒☠☠🌧',
    9: '🔒💣🌧',
}
AbsorbAttributes = {
    -9: '💣🌪️',
    -1: 'Random Att🌪️',
    None: '🔥🌪️',
    0: '🔥🌪️',
    1: '🌊🌪️',
    2: '🌿🌪️',
    3: '💡🌪️',
    4: '🌙🌪️',
    5: '🩹🌪️',
    6: '🗑️🌪️',
    7: '☠🌪️',
    8: '☠☠🌪️',
    9: '💣🌪️',
}
LockedAttributes = {
    -9: '🔒💣🌧',
    -1: 'Random Att',
    None: '🔒🔥',
    0: '🔒🔥',
    1: '🔒🌊',
    2: '🔒🌿',
    3: '🔒💡',
    4: '🔒🌙',
    5: '🔒🩹',
    6: '🔒🗑️',
    7: '🔒☠',
    8: '🔒☠☠',
    9: '🔒💣',
}

Types = {
    0: 'Evo Material',
    1: '⚖',
    2: '🛡️',
    3: '❤',
    4: '🐉',
    5: '😇',
    6: '⚔',
    7: '😈',
    8: '⚙',
    12: 'Awaken Material',
    14: 'Enhance Material',
    15: 'Redeemable Material',
}
"Basically the same skill parser, but this time not using regex"
"Additionally a lot of these are based on t_r's work"
def process_enemy_skill(effect: str, encounter: dict, skill: dict, es: EnemySkill):
    return ""

def attribute_bitmap(bits, inverse=False, bit_len=9):
    if bits is None:
        return []
    if bits == -1:
        return [-1]
    offset = 0
    atts = []
    while offset < bit_len:
        if inverse:
            if (bits >> offset) & 1 == 0:
                atts.append(offset)
        else:
            if (bits >> offset) & 1 == 1:
                atts.append(offset)
        offset += 1
    return atts


def typing_bitmap(bits):
    if bits is None:
        return None
    if bits == -1:
        return []
    offset = 0
    types = []
    while offset < bits.bit_length():
        if (bits >> offset) & 1 == 1:
            types.append(offset)
        offset += 1
    return types


def bind_bitmap(bits) -> List[int]:
    if bits is None:
        return [0]
    targets = []
    if (bits >> 0) & 1 == 1:
        targets.append(1)
    if (bits >> 1) & 1 == 1:
        if len(targets) > 0:
            targets = 2
        else:
            targets.append(3)
    if (bits >> 2) & 1 == 1:
        targets.append(4)
    return targets


def position_bitmap(bits):
    offset = 0
    positions = []
    while offset < bits.bit_length():
        if (bits >> offset) & 1 == 1:
            positions.append(offset + 1)
        offset += 1
    return positions


def positions_2d_bitmap(bits_arr):
    # row check
    rows = []
    for i in range(5):
        if bits_arr[i] is None:
            bits_arr[i] = 0
        is_row = True
        not_row = True
        for j in range(6):
            is_row = is_row and (bits_arr[i] >> j) & 1 == 1
            not_row = not_row and (bits_arr[i] >> j) & 1 != 1
        if is_row:
            rows.append(i + 1)
    if len(rows) == 0:
        rows = None
    # column check
    cols = []
    for j in range(6):
        is_col = True
        for i in range(5):
            is_col = is_col and (bits_arr[i] >> j) & 1 == 1
        if is_col:
            cols.append(j + 1)
    if len(cols) == 0:
        cols = None
    positions = []
    for i in range(5):
        row = [(bits_arr[i] >> j) & 1 for j in range(6)]
        positions.append(row)
    return positions, rows, cols

def attributes_to_emoji(atts, emoji_map = Attributes):
    if not isinstance(atts, list):
        atts = [atts]
    emoji = ''
    for a in atts:
        emoji += emoji_map[a]
    return emoji
def minmax(min, max, extra: str=""):
    if min == max:
        return max + extra
    else:
        return "{}{}-{}{}".format(min, extra, max, extra)

# These are helper level functions
def ESOrbSingleChange(from_attr, to_attr):
    return "{}{}{}".format(Attributes[from_attr], generic_symbols['to'], Attributes[to_attr])
def ESOrbCount(from_attr, to_attr, amount):
    return "{}{}{}{}".format(amount, attributes_to_emoji(from_attr), generic_symbols['to'], attributes_to_emoji(to_attr))
def ESRandomTypeCount(to_attr, amount_types):
    return "{} Random Types{}{}".format(amount_types, generic_symbols['to'], Attributes[to_attr])
def ESColumnRow(pos1, att1, pos2, att2, rc):
    if rc == 0:
        row_col = 'Col:'
    else:
        row_col = 'Row:'
    first = ''
    effect2 = ''
    for p in pos1:
            first = str(p) + ', '
    effect1 = '{}: {}{}{}'.format(row_col, first, generic_symbols['to'], Attributes[att1])
    if pos2:
        second = ''
        for p in pos2:
            second = str(p) + ', '
        effect2 = '{}: {}{}{}'.format(row_col, second, generic_symbols['to'], Attributes[att2])
    return '{} {}'.format(effect1, effect2 or '')
def ESBoardChange(attributes):
    emoji = attributes_to_emoji(attributes)
    return "Board{}{}".format(generic_symbols['to'], emoji)
def ESOrbSeal(positions, turns, row_col):
    if row_col == 0:
        return '{}C: {} for {}'.format(emoji_dict['tape'], ','.join(positions), turns)
    else:
        return '{}R: {} for {}'.format(emoji_dict['tape'], ','.join(positions), turns)

# I don't know what I am doing, start simple by manually doing every skill type
def ES1BindRandom(es: EnemySkill):
    target_count = es.params[1]
    min = es.params[2] or 0
    max = es.params[3]
    return "{}{}Random{}".format(generic_symbols['bind'], target_count, minmax(min, max))
def ES2BindAttribute(es: EnemySkill):
    target = es.params[1]
    min = es.params[2] or 0
    max = es.params[3]
    return "{}{}{}".format(generic_symbols['bind'], Attributes[target], minmax(min, max))
def ES3BindTyping(es: EnemySkill):
    targets = es.params[1]
    min = es.params[2] or 0
    max = es.params[3]
    return "{}{}{}".format(generic_symbols['bind'], Types[targets], minmax(min, max))
def ES4OrbChangeSingle(es: EnemySkill):
    return ESOrbSingleChange(es.params[1], es.params[2])
def ES5Blind(es: EnemySkill):
    # We will process all attacks from the database
    attack = es.params[1]
    return "{}All".format(generic_symbols['blind'])
def ES6Dispel(es: EnemySkill):
    return "Dispel"
def ES7RecoverEnemy(es: EnemySkill):
    min = es.params[1]
    max = es.params[2]
    return "{}{}HP{}{}".format(skills_dict['recover'], minmax(min, max, "%"), generic_symbols['to'], generic_symbols['self'])
def ES8StorePower(es: EnemySkill):
    multiplier = 100 + es.params[1]
    turns = 1
    return "{}{}% for {}".format(emoji_dict['enrage'], multiplier, turns)
def ES12JammerChangeSingle(es: EnemySkill):
    return ESOrbSingleChange(es.params[1], 6)
def ES13JammerChangeRandom(es: EnemySkill):
    return ESRandomTypeCount(6, es.params[1])
def ES14BindSkill(es: EnemySkill):
    min = es.params[1] or 0
    max = es.params[2]
    return "{} for {}".format(emoji_dict['skill_bind'], minmax(min, max))
def ES15AttackMultihit(es: EnemySkill):
    return ""
def ES16Inactivity(es: EnemySkill):
    return emoji_dict['do_nothing']
def ES17AttackUpRemainingEnemies(es: EnemySkill):
    multiplier = es.params[3]
    turns = es.params[2]
    return "{}{}% for {}".format(emoji_dict['enrage'], multiplier, turns)
def ES18AttackUpStatus(es: EnemySkill):
    multiplier = es.params[2]
    turns = es.params[1]
    return "{}{}% for {}".format(emoji_dict['enrage'], multiplier, turns)
def ES19AttackUpCooldown(es: EnemySkill):
    multiplier = es.params[3]
    turns = es.params[2]
    return "{}{}% for {}".format(emoji_dict['enrage'], multiplier, turns)
def ES20StatusShield(es: EnemySkill):
    turns = es.params[1]
    return "{} for {}".format(emoji_dict['status_shield'], turns)
def ES39DebuffMoveTime(es: EnemySkill):
    time = 0
    turns = es.params[1]
    extension = '%'
    if es.params[2] is not None:
        time = -es.params[2] / 10
        seconds = 's'
    elif es.params[3] is not None:
        time = es.params[3]
    else:
        return 'Some time debuff, Not Processed'
    return "{}{}{} for {}".format(emoji_dict['time_debuff'], time , extension, turns)
def ES40EndBattle(es: EnemySkill):
    return 'Battle Ends'
def ES46ChangeAttribute(es: EnemySkill):
    attributes = list(OrderedDict.fromkeys(es.params[1:6]))
    emoji = attributes_to_emoji(attributes)
    return "{}{}{}".format(generic_symbols['self'], generic_symbols['to'], emoji)
def ES47AttackPreemptive(es: EnemySkill):
    return ""
def ES48OrbChangeAttack(es: EnemySkill, orb_from=None, orb_to=None):
    return ESOrbSingleChange(es.params[2], es.params[3])
def ES50Gravity(es: EnemySkill):
    percent = es.params[1]
    return "(-{}%{})".format(percent, emoji_dict['gravity'])
def ES52RecoverEnemyAlly(es: EnemySkill):
    amount = es.params[1]
    return "{}{}%HP{}{}".format(skills_dict['recover'], amount, generic_symbols['to'], 'Ally')
def ES53AbsorbAttribute(es: EnemySkill):
    attributes = attribute_bitmap(es.params[3])
    emoji = attributes_to_emoji(attributes, AbsorbAttributes)
    min_turns = es.params[1] or 0
    max_turns = es.params[2]
    return "{} for {}".format(emoji, minmax(min_turns, max_turns))
def ES54BindTarget(es: EnemySkill):
    targets = bind_bitmap(es.params[1])
    min_turns = es.params[2] or 0
    max_turns = es.params[3]
    return "{}{} for {}".format(generic_symbols["bind"], TargetType[targets[0]], minmax(min_turns, max_turns))
def ES55RecoverPlayer(es: EnemySkill):
    amount = es.params[1]
    return "{}{}%HP{}{}".format(skills_dict['recover'], amount, generic_symbols['to'], 'Player')
def ES56PoisonChangeSingle(es: EnemySkill):
    return ESOrbSingleChange(es.params[1], 7)
def ES57PoisonRandom(es: EnemySkill):
    exclude_hearts = es.params[2] == 1
    return ESOrbSingleChange(-1, 7)
def ES60PoisonChangeRandomCount(es: EnemySkill):
    exclude_hearts = es.params[2] == 1
    return ESOrbCount(-1, 7, int(es.params[1]))
def ES61MortalPoisonChangeRandom(es: EnemySkill):
    return ESOrbCount(-1, 8, es.params[1])
def ES62Blind(es: EnemySkill):
    return ES5Blind(es)
def ES63BindAttack(es: EnemySkill):
    targets = bind_bitmap(es.params[4])
    min_turns = es.params[2] or 0
    max_turns = es.params[3]
    if 'leader' not in ''.join(map(str, targets)):
        target_count = es.params[5]
    if target_count is None:
        return "{}{} for {}".format(generic_symbols["bind"], TargetType[targets[0]], minmax(min_turns, max_turns))
    return "{}{}{} for {}".format(generic_symbols["bind"], target_count, TargetType[targets[0]], minmax(min_turns, max_turns))
def ES64PoisonChangeRandomAttack(es: EnemySkill):
    return ESOrbCount(-1, 7, es.params[2])
def ES65BindRandomSub(es: EnemySkill):
    targets = TargetType['Subs']
    target_count = es.params[1]
    min_turns = es.params[2] or 0
    max_turns = es.params[3]
    return "{}{} {} for {}".format(generic_symbols["bind"], target_count, targets, minmax(min_turns, max_turns))
def ES66Inactivity(es: EnemySkill):
    return ES16Inactivity(es)
def ES67AbsorbCombo(es: EnemySkill):
    threshold = es.params[3]
    min_turns = es.params[1] or 0
    max_turns = es.params[2]
    return "{}Combo{} for {}".format(emoji_dict['combo'], threshold, minmax(min_turns, max_turns))
def ES68Skyfall(es: EnemySkill, locked = False):
    min_turns = es.params[2] or 0
    max_turns = es.params[3]
    attributes = attribute_bitmap(es.params[1])
    chance = es.params[4]
    if not locked:
        return "{}{}% for {}".format(attributes_to_emoji(attributes, SkyfallAttributes), chance, minmax(min_turns, max_turns))
    if locked:
        return "{}{}% for {}".format(attributes_to_emoji(attributes, LockedSkyfallAttributes), chance, minmax(min_turns, max_turns))
def ES69DeathCry(es: EnemySkill):
    return ''
def ES71VoidShield(es: EnemySkill):
    turns = es.params[1]
    void_threshold = es.params[3]
    return "{}{} for {}".format(emoji_dict['void'], void_threshold, turns)
def ES72AttributeResist(es: EnemySkill):
    attributes = attribute_bitmap(es.params[1])
    shield_percent = es.params[2]
    return "{}-{}%".format(attributes_to_emoji(attributes), shield_percent)
def ES73Resolve(es: EnemySkill):
    hp_threshold = es.params[1]
    return "{}{}%".format(emoji_dict['resolve'], hp_threshold)
def ES74DamageShield(es: EnemySkill):
    turns = es.params[1]
    shield_percent = es.params[2]
    emoji = emoji_dict['defense' + shield_percent]
    if emoji is None:
        emoji = emoji_dict['defense'] + shield_percent + '%'
    return "{} for {}".format(emoji, turns)
def ES75LeaderSwap(es: EnemySkill):
    turns = es.params[1]
    return "{} for {}".format(emoji_dict['swap'], turns)
def ES76ColumnSpawnMulti(es: EnemySkill):
    position1 = position_bitmap(es.params[1])
    position2 = position_bitmap(es.params[3])
    att1 = attribute_bitmap(es.params[2])
    att2 = attribute_bitmap(es.params[3])
    return ESColumnRow(position1, att1, position2, att2, 0)
def ES77ColumnSpawnMultiAttack(es: EnemySkill):
    return ES76ColumnSpawnMulti(es)
def ES78RowSpawnMulti(es: EnemySkill):
    position1 = position_bitmap(es.params[1])
    position2 = position_bitmap(es.params[3])
    att1 = attribute_bitmap(es.params[2])
    att2 = attribute_bitmap(es.params[3])
    return ESColumnRow(position1, att1, position2, att2, 1)
def ES79RowSpawnMultiAttack(es: EnemySkill):
    return ES78RowSpawnMulti(es)
def ES81BoardChangeAttackFlat(es: EnemySkill):
    return ESBoardChange(es.params[2:es.params.index(-1)])
def ES82AttackSingleHit(es: EnemySkill):
    return ''
def ES83SkillSet(es: EnemySkill, esd: EnemySkillDatabase):
    # in the database these are the skill1 + skill2 + skill3
    skill_ids = list(filter(None, es.params[1:11]))
    skills = []
    effects = []
    for id in skill_ids:
        skills.append(esd.get_es_from_id(int(id)))
    for skill in skills:
        return 'SkillSet'
    #TODO Finish this
    return ''
def ES84BoardChange(es: EnemySkill):
    return ESBoardChange(attribute_bitmap(es.params[1]))
def ES85BoardChangeAttackBits(es: EnemySkill):
    return ESBoardChange(attribute_bitmap(es.params[2]))
def ES86RecoverEnemy(es: EnemySkill):
    return ES7RecoverEnemy(es)
def ES87AbsorbThreshold(es: EnemySkill):
    turns = es.params[1]
    threshold = es.params[2]
    return "{}{} for {}".format(emoji_dict['damage_absorb'], threshold, turns)
def ES88BindAwoken(es: EnemySkill):
    turns = es.params[1]
    return '{} for {}'.format(emoji_dict['awoken_bind'], turns)
def ES89SkillDelay(es: EnemySkill):
    min_turns = es.params[1] or 0
    max_turns = es.params[2]
    return "{}-[{}]".format(emoji_dict['skill_delay'], minmax(min_turns, max_turns))
def ES92RandomSpawn(es: EnemySkill):
    count = es.params[1]
    attributes = attribute_bitmap(es.params[2])
    ca = []
    condition_attributes = attribute_bitmap(es.params[3], inverse=True)
    if len(condition_attributes) < 6:
        ca = condition_attributes
    conditional = bool(ca)
    if count == 42 and ca:
        return '{}{}{}'.format(attributes_to_emoji(ca), generic_symbols['to'], attributes_to_emoji(attributes))
    else:
        return 'Any {}{}{}'.format(count, generic_symbols['to'], attributes_to_emoji(attributes))
def ES94OrbLock(es: EnemySkill):
    attributes = attribute_bitmap(es.params[1])
    count = es.params[2]
    return '{}:{}'.format(emoji_dict['locked'], attributes_to_emoji(attributes))
def ES95SkillSetOnDeath(es: EnemySkill, esd: EnemySkillDatabase):
    return ES83SkillSet(es, esd)
def ES96SkyfallLocked(es: EnemySkill):
    return ES68Skyfall(es, True)
def ES97BlindStickyRandom(es: EnemySkill):
    turns = es.params[1]
    min_count = es.params[2]
    max_count = es.params[3]
    return "{}{} for {}".format(generic_symbols['super_blind'], minmax(min_count, max_count), turns)
def ES98BlindStickyFixed(es: EnemySkill):
    # Maybe do
    turns = es.params[1]
    positions_map, position_rows, position_cols = positions_2d_bitmap(es.params[2:7])
    return "{}for{}".format(generic_symbols["super_blind"], turns)
def ES99OrbSealColumn(es: EnemySkill):
    turns = es.params[2]
    positions = position_bitmap(es.params[1])
    return ESOrbSeal(positions, turns, 0)
def ES100OrbSealRow(es: EnemySkill):
    turns = es.params[2]
    positions = position_bitmap(es.params[1])
    return ESOrbSeal(positions, turns, 1)
def ES101FixedStart(es: EnemySkill):
    return emoji_dict['starting_position']
def ES102BombRandomSpawn(es: EnemySkill):
    count = es.params[2]
    locked = es.params[8] == 1
    spawn_type = -9 if locked else 9
    return 'Any {}{}{}'.format(count, generic_symbols['to'], attributes_to_emoji([spawn_type]))
def ES103BombFixedSpawn(es: EnemySkill):
    count = es.params[2]
    position_map, position_rows, position_cols = positions_2d_bitmap(es.params[2:7])
    locked = es.params[8] == 1
    all_rows = len(position_rows or []) == 6
    all_cols = len(position_cols or []) == 5
    whole_board = all_rows and all_cols
    spawn_type = -9 if locked else 9
    if whole_board:
        return 'Board{}{}'.format(generic_symbols['to'], attributes_to_emoji([spawn_type]))
    else:
        return '{}'.format(attributes_to_emoji([spawn_type]))
def ES104Cloud(es: EnemySkill):
    turns = es.params[1]
    width = es.params[2]
    height = es.params[3]
    y = es.params[4]
    x = es.params[5]
    if x is None and y is None:
        return "{}{}x{} for {}".format(emoji_dict['cloud'], width, height, turns)
    row = x or 'Random'
    col = y or 'Random'
    return "{}{}x{} at [{},{}] for {}".format(emoji_dict['cloud'], width, height, row, col, turns)
def ES105DebuffRCV(es: EnemySkill):
    turns = es.params[1]
    amount = es.params[2]
    emoji = emoji_dict['rcv_debuff'] if es.params[2] < 100 else emoji_dict['rcv_buff']
    return '{}{}% for {}'.format(emoji, amount, turns)
def ES106TurnChangePassive(es: EnemySkill):
    hp_threshold = es.params[1]
    turn = es.params[2]
    return "{}{}{} at {}%HP".format(emoji_dict['turn_change'], generic_symbols['to'], turn, hp_threshold)
def ES107AttributeUnmatchable(es: EnemySkill):
    turns = es.params[1]
    attributes = attribute_bitmap(es.params[2])
    return '{} for {}'.format(attributes_to_emoji(attributes, UnmatchableAttributes), turns)
def ES108OrbChangeAttackBits(es: EnemySkill):
    return ESOrbSingleChange(es.params[2], es.params[3])
def ES109SpinnerRandom(es: EnemySkill):
    turns = es.params[1]
    speed = es.params[2]
    count = es.params[3]
    speed_str = '{:.1f}s'.format(speed / 100)
    return "{}{}Random {} for {}".format(emoji_dict['roulette'], count, speed_str, turns)
def ES110SpinnerFixed(es: EnemySkill):
    position_map, position_rows, position_cols = positions_2d_bitmap(es.params[3:8])
    turns = es.params[1]
    speed = es.params[2]
    speed_str = '{:.1f}s'.format(speed / 100)
    return '{}{} for {}'.format(emoji_dict['roulette'], speed_str, turns)
def ES111MaxHPChange(es: EnemySkill):
    turns = es.params[3]
    max_hp = None
    percent = None
    if es.params[1] is not None:
        max_hp = es.params[1]
        percent = True
    elif es.params[2] is not None:
        max_hp = es.params[2]
        percent = False
    if percent:
        return "{}= {}% for {}".format(generic_symbols['health'], max_hp, turns)
    else:
        return "{}= {} for {}".format(generic_symbols['health'], max_hp, turns)
def ES112FixedTarget(es: EnemySkill):
    turn_count = es.params[1]
    return "{}{}".format(emoji_dict['force_target'], turn_count)
def ES118TypeResist(es: EnemySkill):
    types = typing_bitmap(es.params[1])
    shield = es.params[2]
    return "{}-{}%".format(attributes_to_emoji(types, Types), shield)
def ES119InvulnerableOn(es: EnemySkill):
    return '{}'.format(emoji_dict['invincible'])
def ES121InvulnerableOff(es: EnemySkill):
    return '{}'.format(emoji_dict['invincible_off'])
def ES122TurnChangeRemainingEnemies(es: EnemySkill):
    turn_counter = es.params[2]
    enemy_count = es.params[1]
    return "{}{}{} when enemies={}".format(emoji_dict['turn_change'], generic_symbols['to'], turn_counter, enemy_count)
def ES123InvulnerableOnHexazeon(es: EnemySkill):
    return ES119InvulnerableOn(es)
def ES125LeaderAlter(es: EnemySkill):
    turns = es.params[1]
    target_card = es.params[2]
    return "{}[{}] for {}".format(emoji_dict['leader_alter'], target_card, turns)
def ES126BoardSizeChange(es: EnemySkill):
    turns = es.params[1]
    board_size = es.params[2]
    size = {1: '7x6', 2: '5x4', 3: '6x5'}.get(board_size, 'unknown')
    return "{}{} for {}".format(board_size, emoji_dict['board_size'], turns)
def ES127NoSkyfall(es: EnemySkill):
    turns = es.params[2]
    return '{} for {}'.format(emoji_dict['no_skyfall'], turns)
def ES128BlindStickySkyfall(es: EnemySkill):
    turns = es.params[1]
    chance = es.params[2]
    blind_turns = es.params[13]
    return "{}{}% for {}".format(skyfall_symbols["super_blind"], chance, turns)
def ES129SuperResolve(es: EnemySkill):
    thresh = es.params[1]
    remaining = es.params[2] #idk when this would ever be useful
    return "{}{}".format(emoji_dict['super_resolve'], thresh)
def ES130DebuffAtk(es: EnemySkill):
    turns = es.params[1]
    amount = es.params[2]
    return "{}{}% for {}".format(emoji_dict['atk_debuff'], amount, turns)
def ES131ComboSkyfall(es: EnemySkill):
    turns = es.params[2]
    chance = es.params[3]
    return '{}{}% for {}'.format(skyfall_symbols['combo'], chance, turns)
def ESUnknown(es: EnemySkill):
    return 'Unprocessed, {}'.format(es.type)
def ESConditional(es: EnemySkill):
    return None

