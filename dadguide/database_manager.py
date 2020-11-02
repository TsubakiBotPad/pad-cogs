from datetime import datetime
import sqlite3 as lite
import romkan
import logging

import pytz
import re

from collections import defaultdict

import tsutils
from dadguide.models.enum_types import Attribute, MonsterType

logger = logging.getLogger('red.padbot-cogs.dadguide.database_manager')


class DadguideTableNotFound(Exception):
    def __init__(self, table_name):
        self.message = '{} not found'.format(table_name)


class DadguideDatabase(object):
    def __init__(self, data_file):
        self._con = lite.connect(data_file, detect_types=lite.PARSE_DECLTYPES)
        self._con.row_factory = lite.Row

    def __del__(self):
        self.close()
        logger.info("Garbage Collecting Old Database")

    def has_database(self):
        return self._con is not None

    def close(self):
        if self._con:
            self._con.close()
        self._con = None

    @staticmethod
    def select_builder(tables, key=None, where=None, order=None, distinct=False):
        if distinct:
            SELECT_FROM = 'SELECT DISTINCT {fields} FROM {first_table}'
        else:
            SELECT_FROM = 'SELECT {fields} FROM {first_table}'
        WHERE = 'WHERE {condition}'
        JOIN = 'LEFT JOIN {other_table} ON {first_table}.{key}={other_table}.{key}'
        ORDER = 'ORDER BY {order}'
        first_table = None
        fields_lst = []
        other_tables = []
        for table, fields in tables.items():
            if fields is not None:
                fields_lst.extend(['{}.{}'.format(table, f) for f in fields])
            if first_table is None:
                first_table = table
                if key is None:
                    break
            else:
                other_tables.append(table)
        query = [SELECT_FROM.format(first_table=first_table, fields=', '.join(fields_lst))]
        prev_table = first_table
        if key:
            for k, other in zip(key, other_tables):
                query.append(JOIN.format(first_table=prev_table, other_table=other, key=k))
                prev_table = other
        if where:
            query.append(WHERE.format(condition=where))
        if order:
            query.append(ORDER.format(order=order))
        return ' '.join(query)

    def query_one(self, query, param, d_type, graph=None):
        cursor = self._con.cursor()
        cursor.execute(query, param)
        res = cursor.fetchone()
        if res is not None:
            if issubclass(d_type, DadguideItem):
                return d_type(res, graph=graph)
            else:
                return d_type(res)
        return None

    def as_generator(self, cursor, d_type, graph=None):
        res = cursor.fetchone()
        while res is not None:
            if issubclass(d_type, DadguideItem):
                yield d_type(res, graph=graph)
            else:
                yield d_type(res)
            res = cursor.fetchone()

    def query_many(self, query, param, d_type, idx_key=None, as_generator=False, graph=None):
        cursor = self._con.cursor()
        cursor.execute(query, param)
        if cursor.rowcount == 0:
            return []
        if as_generator:
            return (d_type(res, graph=graph)
                    if issubclass(d_type, DadguideItem)
                    else d_type(res)
                    for res in cursor.fetchall())
        else:
            if idx_key is None:
                if issubclass(d_type, DadguideItem):
                    return [d_type(res, graph=graph) for res in cursor.fetchall()]
                else:
                    return [d_type(res) for res in cursor.fetchall()]
            else:
                if issubclass(d_type, DadguideItem):
                    return DictWithAttrAccess(
                        {res[idx_key]: d_type(res, graph=graph) for res in cursor.fetchall()})
                else:
                    return DictWithAttrAccess({res[idx_key]: d_type(res) for res in cursor.fetchall()})

    def select_one_entry_by_pk(self, pk, d_type, graph=None):
        return self.query_one(
            self.select_builder(
                tables={d_type.TABLE: d_type.FIELDS},
                where='{}.{}=?'.format(d_type.TABLE, d_type.PK)),
            (pk,),
            d_type, graph=graph)

    def get_table_fields(self, table_name: str):
        # SQL inject vulnerable :v
        table_info = self.query_many('PRAGMA table_info(' + table_name + ')', (), dict)
        pk = None
        fields = []
        for c in table_info:
            if c['pk'] == 1:
                pk = c['name']
            fields.append(c['name'])
        if len(fields) == 0:
            raise DadguideTableNotFound(table_name)
        return fields, pk


def enum_or_none(enum, value, default=None):
    if value is not None:
        return enum(value)
    else:
        return default


class DictWithAttrAccess(dict):
    def __init__(self, item):
        super(DictWithAttrAccess, self).__init__(item)
        self.__dict__ = self


class DadguideItem(DictWithAttrAccess):
    """
    Base class for all items loaded from DadGuide.
    Is a dict with attr access.
    """
    TABLE = None
    FIELDS = '*'
    PK = None
    AS_BOOL = ()

    def __init__(self, item, **kwargs):
        super(DadguideItem, self).__init__(item)
        for k in self.AS_BOOL:
            self[k] = bool(self[k])

    def key(self):
        return self[self.PK]


class DgAwakening(DadguideItem):
    TABLE = 'awakenings'
    PK = 'awakening_id'
    AS_BOOL = ['is_super']

    def __init__(self, item, **kwargs):
        super(DgAwakening, self).__init__(item)

    @property
    def name(self):
        return self.name_en if self.name_en is not None else self.name_ja


class DgEvolution(DadguideItem):
    TABLE = 'evolutions'
    PK = 'evolution_id'

    def __init__(self, item, **kwargs):
        super(DgEvolution, self).__init__(item)
        self.evolution_type = EvoType(self.evolution_type)


class DgDungeon(DadguideItem):
    TABLE = 'dungeons'
    PK = 'dungeon_id'


class DgScheduledEvent(DadguideItem):
    TABLE = 'schedule'
    PK = 'event_id'

    def __init__(self, item, **graph):
        super(DgScheduledEvent, self).__init__(item)

    @property
    def open_datetime(self):
        return datetime.utcfromtimestamp(self.start_timestamp).replace(tzinfo=pytz.UTC)

    @open_datetime.setter
    def open_datetime(self, value):
        self.start_timestamp = int(value.timestamp())

    @property
    def close_datetime(self):
        return datetime.utcfromtimestamp(self.end_timestamp).replace(tzinfo=pytz.UTC)

    @close_datetime.setter
    def close_datetime(self, value):
        self.end_timestamp = int(value.timestamp())


class DgMonster(DadguideItem):
    TABLE = 'monsters'
    PK = 'monster_id'
    AS_BOOL = ('on_jp', 'on_na', 'on_kr', 'has_animation', 'has_hqimage')

    def __init__(self, item, graph):
        super(DgMonster, self).__init__(item)

        self._graph = graph

        self.roma_subname = None
        if self.name_en == self.name_ja:
            self.roma_subname = make_roma_subname(self.name_ja)
        else:
            # Remove annoying stuff from NA names, like Jörmungandr
            self.name_en = tsutils.rmdiacritics(self.name_en)

        self.name_en = self.name_en_override or self.name_en

        self.attr1 = enum_or_none(Attribute, self.attribute_1_id, Attribute.Nil)
        self.attr2 = enum_or_none(Attribute, self.attribute_2_id, Attribute.Nil)

        self.type1 = enum_or_none(MonsterType, self.type_1_id)
        self.type2 = enum_or_none(MonsterType, self.type_2_id)
        self.type3 = enum_or_none(MonsterType, self.type_3_id)
        self.types = list(filter(None, [self.type1, self.type2, self.type3]))

        self.in_pem = bool(self.pal_egg)
        self.in_rem = bool(self.rem_egg)

        self.awakenings = sorted(self.node['model'].awakenings, key=lambda a: a.order_idx)

        self.superawakening_count = sum(int(a.is_super) for a in self.awakenings)

        self.is_inheritable = bool(self.inheritable)

        self.is_equip = any([x.awoken_skill_id == 49 for x in self.awakenings])

    @property
    def node(self):
        return self._graph.nodes[self.monster_id]

    @property
    def monster_no(self):
        return self.monster_id

    def stat(self, key, lv, plus=99, inherit=False, is_plus_297=True):
        s_min = float(self[key + '_min'])
        s_max = float(self[key + '_max'])
        if self.level > 1:
            s_val = s_min + (s_max - s_min) * ((min(lv, self.level) - 1) / (self.level - 1)) ** self[key + '_scale']
        else:
            s_val = s_min
        if lv > 99:
            s_val *= 1 + (self.limit_mult / 11 * (lv - 99)) / 100
        plus_dict = {'hp': 10, 'atk': 5, 'rcv': 3}
        s_val += plus_dict[key] * max(min(plus, 99), 0)
        if inherit:
            inherit_dict = {'hp': 0.10, 'atk': 0.05, 'rcv': 0.15}
            if not is_plus_297:
                s_val -= plus_dict[key] * max(min(plus, 99), 0)
            s_val *= inherit_dict[key]
        return int(round(s_val))

    def stats(self, lv=99, plus=0, inherit=False):
        is_plus_297 = False
        if plus == 297:
            plus = (99, 99, 99)
            is_plus_297 = True
        elif plus == 0:
            plus = (0, 0, 0)
        hp = self.stat('hp', lv, plus[0], inherit, is_plus_297)
        atk = self.stat('atk', lv, plus[1], inherit, is_plus_297)
        rcv = self.stat('rcv', lv, plus[2], inherit, is_plus_297)
        weighted = int(round(hp / 10 + atk / 5 + rcv / 3))
        return hp, atk, rcv, weighted

    @property
    def active_skill(self):
        return self.node['model'].active_skill

    @property
    def leader_skill(self):
        return self.node['model'].leader_skill

    @property
    def killers(self):
        type_to_killers_map = {
            MonsterType.God: ['Devil'],
            MonsterType.Devil: ['God'],
            MonsterType.Machine: ['God', 'Balance'],
            MonsterType.Dragon: ['Machine', 'Healer'],
            MonsterType.Physical: ['Machine', 'Healer'],
            MonsterType.Attacker: ['Devil', 'Physical'],
            MonsterType.Healer: ['Dragon', 'Attacker'],
        }
        if MonsterType.Balance in self.types:
            return ['Any']
        killers = set()
        for t in self.types:
            killers.update(type_to_killers_map.get(t, []))
        return sorted(killers)

    @property
    def in_mpshop(self):
        return self.buy_mp is not None

    @property
    def history_us(self):
        return '[{}] New Added'.format(self.reg_date)

    def __repr__(self):
        return "DgMonster<{} ({})>".format(self.name_en, self.monster_no)

    def __eq__(self, other):
        return isinstance(other, DgMonster) and self.monster_id == other.monster_id

    def __hash__(self):
        return hash(("DgMonster", self.monster_id))


def make_roma_subname(name_ja):
    subname = re.sub(r'[＝]', '', name_ja)
    subname = re.sub(r'[「」]', '・', subname)
    adjusted_subname = ''
    for part in subname.split('・'):
        roma_part = romkan.to_roma(part)
        if part != roma_part and not tsutils.containsJa(roma_part):
            adjusted_subname += ' ' + roma_part.strip('-')
    return adjusted_subname.strip()


class PotentialMatches(object):
    def __init__(self):
        self.match_list = set()

    def add(self, m):
        self.match_list.add(m)

    def update(self, monster_list):
        self.match_list.update(monster_list)

    def length(self):
        return len(self.match_list)

    def remove_potential_matches_without_all_prefixes(self, query_prefixes):
        to_remove = set()
        for m in self.match_list:
            for prefix in query_prefixes:
                if prefix not in m.prefixes:
                    to_remove.add(m)
                    break
        self.match_list.difference_update(to_remove)

    def get_monsters_from_potential_pantheon_match(self, pantheon, pantheon_nick_to_name, pantheons):
        full_name = pantheon_nick_to_name[pantheon]
        self.update(pantheons[full_name])

    def pick_best_monster(self):
        return max(self.match_list, key=lambda x: (not x.is_low_priority, x.rarity, x.monster_no_na))


class NamedMonsterGroup(object):
    def __init__(self, evolution_tree: list, basename_overrides: list):
        self.is_low_priority = (
                        self._is_low_priority_monster(evolution_tree[0])
                        or self._is_low_priority_group(evolution_tree))

        base_monster = evolution_tree[0]
        self.group_size = len(evolution_tree)
        self.base_monster_no = base_monster.monster_id
        self.base_monster_no_na = base_monster.monster_no_na

        self.monster_no_to_basename = {
            m.monster_id: self._compute_monster_basename(m) for m in evolution_tree
        }

        self.computed_basename = self._compute_group_basename(evolution_tree)
        self.computed_basenames = set([self.computed_basename])
        if '-' in self.computed_basename:
            self.computed_basenames.add(self.computed_basename.replace('-', ' '))

        self.basenames = basename_overrides or self.computed_basenames

    def _compute_monster_basename(self, m: DgMonster):
        basename = m.name_en.lower()
        if ',' in basename:
            name_parts = basename.split(',')
            if name_parts[1].strip().startswith('the '):
                # handle names like 'xxx, the yyy' where xxx is the name
                basename = name_parts[0]
            else:
                # otherwise, grab the chunk after the last comma
                basename = name_parts[-1]

        for x in ['awoken', 'reincarnated']:
            if basename.startswith(x):
                basename = basename.replace(x, '')

        # Fix for DC collab garbage
        basename = basename.replace('(comics)', '')
        basename = basename.replace('(film)', '')

        return basename.strip()

    def _compute_group_basename(self, monsters):
        """Computes the basename for a group of monsters.

        Prefer a basename with the largest count across the group. If all the
        groups have equal size, prefer the lowest monster number basename.
        This monster in general has better names, particularly when all the
        names are unique, e.g. for male/female hunters."""

        def count_and_id():
            return [0, 0]

        basename_to_info = defaultdict(count_and_id)

        for m in monsters:
            basename = self.monster_no_to_basename[m.monster_id]
            entry = basename_to_info[basename]
            entry[0] += 1
            entry[1] = max(entry[1], m.monster_id)

        entries = [[count_id[0], -1 * count_id[1], bn] for bn, count_id in basename_to_info.items()]
        return max(entries)[2]

    def _is_low_priority_monster(self, m: DgMonster):
        lp_types = [MonsterType.Evolve, MonsterType.Enhance, MonsterType.Awoken, MonsterType.Vendor]
        lp_substrings = ['tamadra']
        lp_min_rarity = 2
        name = m.name_en.lower()

        failed_type = m.type1 in lp_types
        failed_ss = any([x in name for x in lp_substrings])
        failed_rarity = m.rarity < lp_min_rarity
        failed_chibi = name == m.name_en and m.name_en != m.name_ja
        failed_equip = m.is_equip
        return failed_type or failed_ss or failed_rarity or failed_chibi or failed_equip

    def _is_low_priority_group(self, mg: list):
        lp_grp_min_rarity = 5
        max_rarity = max(m.rarity for m in mg)
        failed_max_rarity = max_rarity < lp_grp_min_rarity
        return failed_max_rarity


class NamedMonster(object):
    def __init__(self, monster: DgMonster, monster_group: NamedMonsterGroup, prefixes: set, extra_nicknames: set, db_context=None):
        # Must not hold onto monster or monster_group!

        # Hold on to the IDs instead
        self.monster_id = monster.monster_id
        self.monster_no_na = monster.monster_no_na
        self.monster_no_jp = monster.monster_no_jp

        # ID of the root of the tree for this monster
        self.base_monster_no = monster_group.base_monster_no
        self.base_monster_no_na = monster_group.base_monster_no_na

        # This stuff is important for nickname generation
        self.group_basenames = monster_group.basenames
        self.prefixes = prefixes

        # Pantheon
        series = db_context.graph.get_monster(monster.monster_no).series
        self.series = series.name if series else None

        # Data used to determine how to rank the nicknames
        self.is_low_priority = monster_group.is_low_priority or monster.is_equip
        self.group_size = monster_group.group_size
        self.rarity = monster.rarity

        # Used in fallback searches
        self.name_en = monster.name_en
        self.name_ja = monster.name_ja

        # These are just extra metadata
        self.monster_basename = monster_group.monster_no_to_basename[self.monster_id]
        self.group_computed_basename = monster_group.computed_basename
        self.extra_nicknames = extra_nicknames

        # Compute any extra prefixes
        if self.monster_basename in ('ana', 'ace'):
            self.prefixes.add(self.monster_basename)

        # Compute extra basenames by checking for two-word basenames and using the second half
        self.two_word_basenames = set()
        for basename in self.group_basenames:
            basename_words = basename.split(' ')
            if len(basename_words) == 2:
                self.two_word_basenames.add(basename_words[1])

        # The primary result nicknames
        self.final_nicknames = set()
        # Set the configured override nicknames
        self.final_nicknames.update(self.extra_nicknames)
        # Set the roma subname for JP monsters
        if monster.roma_subname:
            self.final_nicknames.add(monster.roma_subname)

        # For each basename, add nicknames
        for basename in self.group_basenames:
            # Add the basename directly
            self.final_nicknames.add(basename)
            # Add the prefix plus basename, and the prefix with a space between basename
            for prefix in self.prefixes:
                self.final_nicknames.add(prefix + basename)
                self.final_nicknames.add(prefix + ' ' + basename)

        self.final_two_word_nicknames = set()
        # Slightly different process for two-word basenames. Does this make sense? Who knows.
        for basename in self.two_word_basenames:
            self.final_two_word_nicknames.add(basename)
            # Add the prefix plus basename, and the prefix with a space between basename
            for prefix in self.prefixes:
                self.final_two_word_nicknames.add(prefix + basename)
                self.final_two_word_nicknames.add(prefix + ' ' + basename)
