from enum import Enum
from datetime import datetime
import sqlite3 as lite
import shutil
import romkan
import logging
import pytz
import difflib
import os
import re
from discord.utils import find as find_first
from collections import OrderedDict, defaultdict, deque

from redbot.core.utils import AsyncIter
from redbot.core import data_manager
import tsutils

logger = logging.getLogger('red.padbot-cogs.dadguide.database_manager')

def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='dadguide')), file_name)

DB_DUMP_FILE = _data_file('dadguide.sqlite')
DB_DUMP_WORKING_FILE = _data_file('dadguide_working.sqlite')


class Attribute(Enum):
    """Standard 5 PAD colors in enum form. Values correspond to DadGuide values."""
    Fire = 0
    Water = 1
    Wood = 2
    Light = 3
    Dark = 4
    Unknown = 5
    Nil = 6


class MonsterType(Enum):
    Evolve = 0
    Balance = 1
    Physical = 2
    Healer = 3
    Dragon = 4
    God = 5
    Attacker = 6
    Devil = 7
    Machine = 8
    Awoken = 12
    Enhance = 14
    Vendor = 15


class EvoType(Enum):
    """Evo types supported by DadGuide. Numbers correspond to their id values."""
    Base = 0  # Represents monsters who didn't require evo
    Evo = 1
    UvoAwoken = 2
    UuvoReincarnated = 3


class InternalEvoType(Enum):
    """Evo types unsupported by DadGuide."""
    Base = ""
    Normal = ""
    Ultimate = ""
    Reincarnated = "Reincarnated"
    Assist = "Assist"
    Pixel = "Pixel"
    SuperReincarnated = "Super Reincarnated"


class Server(Enum):
    JP = 0
    NA = 1
    KR = 2


class DadguideTableNotFound(Exception):
    def __init__(self, table_name):
        self.message = '{} not found'.format(table_name)


def load_database(existing_db):
    # Release the handle to the database file if it has one
    if existing_db:
        existing_db.close()
    # Overwrite the working copy so we can open a handle to it without affecting future downloads
    if os.path.exists(DB_DUMP_FILE):
        shutil.copy2(DB_DUMP_FILE, DB_DUMP_WORKING_FILE)
    # Open the new working copy.
    return DadguideDatabase(data_file=DB_DUMP_WORKING_FILE)


class DadguideDatabase(object):
    def __init__(self, data_file):
        self._con = lite.connect(data_file, detect_types=lite.PARSE_DECLTYPES)
        self._con.row_factory = lite.Row


        self._monsters = None
        self.expiry = 0

    def has_database(self):
        return self._con is not None

    def close(self):
        self._con.close()
        self._con = None

    @staticmethod
    def _select_builder(tables, key=None, where=None, order=None, distinct=False):
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

    def _query_one(self, query, param, d_type):
        cursor = self._con.cursor()
        cursor.execute(query, param)
        res = cursor.fetchone()
        if res is not None:
            if issubclass(d_type, DadguideItem):
                return d_type(res, self)
            else:
                return d_type(res)
        return None

    def _as_generator(self, cursor, d_type):
        res = cursor.fetchone()
        if issubclass(d_type, DadguideItem):
            while res is not None:
                yield d_type(res, self)
                res = cursor.fetchone()
        else:
            while res is not None:
                yield d_type(res)
                res = cursor.fetchone()

    def _query_many(self, query, param, d_type, idx_key=None, as_generator=False):
        cursor = self._con.cursor()
        cursor.execute(query, param)
        if cursor.rowcount == 0:
            return []
        if as_generator:
            return self._as_generator(cursor, d_type)
        else:
            if idx_key is None:
                return [d_type(res, self) for res in cursor.fetchall()]
            else:
                return DictWithAttrAccess({res[idx_key]: d_type(res, self) for res in cursor.fetchall()})

    def _max_id(self):
        cursor = self._con.cursor()
        cursor.execute("SELECT MAX(monster_id) FROM monsters WHERE monster_id < 10000")
        return cursor.fetchone()['MAX(monster_id)']

    def _select_one_entry_by_pk(self, pk, d_type):
        return self._query_one(
            self._select_builder(
                tables={d_type.TABLE: d_type.FIELDS},
                where='{}.{}=?'.format(d_type.TABLE, d_type.PK)),
            (pk,),
            d_type)

    def _get_table_fields(self, table_name: str):
        # SQL inject vulnerable :v
        table_info = self._query_many('PRAGMA table_info(' + table_name + ')', (), dict)
        pk = None
        fields = []
        for c in table_info:
            if c['pk'] == 1:
                pk = c['name']
            fields.append(c['name'])
        if len(fields) == 0:
            raise DadguideTableNotFound(table_name)
        return fields, pk

    def get_active_skill(self, active_skill_id: int):
        return self._select_one_entry_by_pk(active_skill_id, DgActiveSkill)

    def get_leader_skill(self, leader_skill_id: int):
        return self._select_one_entry_by_pk(leader_skill_id, DgLeaderSkill)

    def get_awoken_skill(self, awoken_skill_id):
        return self._select_one_entry_by_pk(awoken_skill_id, DgAwokenSkill)

    def get_awoken_skill_ids(self):
        SELECT_AWOKEN_SKILL_IDS = 'SELECT awoken_skill_id from awoken_skills'
        return [r.awoken_skill_id for r in
                self._query_many(SELECT_AWOKEN_SKILL_IDS, (), DadguideItem, as_generator=True)]

    def get_monsters_by_awakenings(self, awoken_skill_id: int):
        return self._query_many(
            self._select_builder(
                tables=OrderedDict({
                    DgMonster.TABLE: DgMonster.FIELDS,
                    DgAwakening.TABLE: None,
                }),
                where='{}.awoken_skill_id=?;'.format(DgAwakening.TABLE),
                key=('monster_id',),
                distinct=True
            ),
            (awoken_skill_id,),
            DgMonster)

    def get_awakenings_by_monster(self, monster_id, is_super=None):
        if is_super is None:
            where = '{0}.monster_id=?'.format(DgAwakening.TABLE)
            param = (monster_id,)
        else:
            where = '{0}.monster_id=? AND {0}.is_super=?'.format(DgAwakening.TABLE)
            param = (monster_id, is_super)
        return self._query_many(
            self._select_builder(
                tables={DgAwakening.TABLE: DgAwakening.FIELDS},
                where=where,
                order='order_idx ASC'
            ),
            param,
            DgAwakening)

    def get_drop_dungeons(self, monster_id):
        return self._query_many(
            self._select_builder(
                tables=OrderedDict({
                    DgDungeon.TABLE: DgDungeon.FIELDS,
                    DgEncounter.TABLE: None,
                    DgDrop.TABLE: None,
                }),
                where='{0}.monster_id=?'.format(DgDrop.TABLE),
                key=(DgDungeon.PK, DgEncounter.PK)
            ),
            (monster_id,),
            DgDungeon)

    def monster_is_farmable(self, monster_id):
        return self._query_one(
            self._select_builder(
                tables={DgDrop.TABLE: DgDrop.FIELDS},
                where='{0}.monster_id=?'.format(DgDrop.TABLE)
            ),
            (monster_id,),
            DgDrop) is not None

    def monster_in_rem(self, monster_id):
        return self._query_one(
            self._select_builder(
                tables={DgMonster.TABLE: ('rem_egg',)},
                where='{0}.monster_id=? AND rem_egg=1'.format(DgMonster.TABLE)
            ),
            (monster_id,),
            DgDrop) is not None

    def monster_in_pem(self, monster_id):
        return self._query_one(
            self._select_builder(
                tables={DgMonster.TABLE: ('pal_egg',)},
                where='{0}.monster_id=? AND pal_egg=1'.format(DgMonster.TABLE)
            ),
            (monster_id,),
            DgDrop) is not None

    def monster_in_mp_shop(self, monster_id):
        return self._query_one(
            self._select_builder(
                tables={DgMonster.TABLE: ('buy_mp',)},
                where='{0}.monster_id=? AND buy_mp IS NOT NULL'.format(DgMonster.TABLE)
            ),
            (monster_id,),
            DgDrop) is not None

    def get_prev_evolution_by_monster(self, monster_id):
        return self._query_one(
            self._select_builder(
                tables={DgEvolution.TABLE: DgEvolution.FIELDS},
                where='{}.to_id=?'.format(DgEvolution.TABLE)
            ),
            (monster_id,),
            DgEvolution)

    def get_next_evolutions_by_monster(self, monster_id):
        return self._query_many(
            self._select_builder(
                tables={DgEvolution.TABLE: DgEvolution.FIELDS},
                where='{}.from_id=?'.format(DgEvolution.TABLE)
            ),
            (monster_id,),
            DgEvolution,
            as_generator=True)

    def get_base_monster_by_monster(self, monster_id):
        base = {'from_id': monster_id, 'to_id': monster_id}
        lastbase = None
        while base != None:
            lastbase = base
            base = self.get_prev_evolution_by_monster(base['from_id'])
        return lastbase

    def get_all_evolutions_by_monster(self, monster_id):
        base = self.get_base_monster_by_monster(monster_id)
        queue = [base]

        while queue:
            curr = queue.pop(0)
            yield curr
            queue.extend(self.get_next_evolutions_by_monster(curr['to_id']))

    def get_evolution_by_material(self, monster_id):
        return self._query_many(
            self._select_builder(
                tables={DgEvolution.TABLE: DgEvolution.FIELDS},
                where=' OR '.join(['{}.mat_{}_id=?'.format(DgEvolution.TABLE, i) for i in range(1, 6)])
            ),
            (monster_id,) * 5,
            DgEvolution)

    def get_base_monster_ids(self):
        SELECT_BASE_MONSTER_ID = '''
            SELECT evolutions.from_id as monster_id FROM evolutions WHERE evolutions.from_id NOT IN (SELECT DISTINCT evolutions.to_id FROM evolutions)
            UNION
            SELECT monsters.monster_id FROM monsters WHERE monsters.monster_id NOT IN (SELECT evolutions.from_id FROM evolutions UNION SELECT evolutions.to_id FROM evolutions)'''
        return self._query_many(
            SELECT_BASE_MONSTER_ID,
            (),
            DictWithAttrAccess,
            as_generator=True)

    def get_evolution_tree_ids(self, base_monster_id):
        # is not a tree i lied
        base_id = base_monster_id
        evolution_tree = [base_id]
        n_evos = deque()
        n_evos.append(base_id)
        while len(n_evos) > 0:
            n_evo_id = n_evos.popleft()
            for e in self.get_next_evolutions_by_monster(n_evo_id):
                n_evos.append(e.to_id)
                evolution_tree.append(e.to_id)
        return evolution_tree

    def monster_id_to_no(self, monster_id, region=Server.JP):
        res = self._query_one(
            self._select_builder(
                tables={DgMonster.TABLE: ('monster_no_{}'.format(region.name.lower()),)},
                where='{}.monster_id=?'.format(DgMonster.TABLE)
            ),
            (monster_id,),
            DictWithAttrAccess)
        for k in res:
            return res[k]

    def get_series(self, series_id: int):
        return self._select_one_entry_by_pk(series_id, DgSeries)

    def _get_monsters_where(self, where, param):
        return self._query_many(
            self._select_builder(
                tables={DgMonster.TABLE: DgMonster.FIELDS},
                where=where
            ),
            param,
            DgMonster)

    def get_monsters_by_series(self, series_id: int):
        return self._get_monsters_where('{}.series_id=?'.format(DgMonster.TABLE), (series_id,))

    def get_monsters_by_active(self, active_skill_id: int):
        return self._get_monsters_where('{}.active_skill_id=?'.format(DgMonster.TABLE), (active_skill_id,))

    def get_monster_evo_gem(self, name: str, region='jp'):
        gem_suffix = {
            'ja': 'の希石',
            'en': '\'s Gem',
            'ko': ' 의 휘석'
        }
        if region not in gem_suffix:
            return None
        non_gem_name = name.replace(gem_suffix[region], '')
        if non_gem_name == name:
            return None
        return self._query_one(
            self._select_builder(
                tables={DgMonster.TABLE: DgMonster.FIELDS},
                where='{0}.name_{1}=? AND {0}.leader_skill_id=10628'.format(DgMonster.TABLE, region)
            ),
            (non_gem_name,),
            DgMonster)

    def get_na_only_monsters(self):
        return self._get_monsters_where(
            '{0}.monster_id != {0}.monster_no_na AND {0}.monster_no_jp == {0}.monster_no_na '.format(DgMonster.TABLE),
            ())

    def get_monster_query(self, monster_id: int):
        return self._select_one_entry_by_pk(monster_id, DgMonster)

    def get_monster(self, monster_id: int):
        for monster in self.get_all_monsters():
            if monster['monster_id'] == monster_id:
                return DgMonster(monster, self)

    def get_all_monster_ja_name(self, as_generator=True):
        return self._query_many(self._select_builder(tables={DgMonster.TABLE: ('name_ja',)}), (), DictWithAttrAccess,
                                as_generator=as_generator)

    def get_all_monsters_query(self, as_generator=True):
        return self._query_many(self._select_builder(tables={DgMonster.TABLE: DgMonster.FIELDS}), (), DgMonster,
                                as_generator=as_generator)

    def get_all_monsters(self):
        if self._monsters == None or self.expiry < datetime.now().timestamp() + 60*60:
            self._monsters = self.get_all_monsters_query(False)
            self.expiry = int(datetime.now().timestamp())
        return self._monsters

    def get_all_events(self, as_generator=True):
        return self._query_many(self._select_builder(tables={DgScheduledEvent.TABLE: DgScheduledEvent.FIELDS}), (),
                                DgScheduledEvent,
                                as_generator=as_generator)

    def get_dungeon_by_id(self, dungeon_id: int):
        return self._select_one_entry_by_pk(dungeon_id, DgDungeon)


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

    def __init__(self, item, database):
        super(DadguideItem, self).__init__(item)
        self._database = database
        for k in self.AS_BOOL:
            self[k] = bool(self[k])

    def key(self):
        return self[self.PK]


class DgActiveSkill(DadguideItem):
    TABLE = 'active_skills'
    PK = 'active_skill_id'

    @property
    def monsters(self):
        return self._database.get_monsters_by_active(self.active_skill_id)

    @property
    def skillups(self):
        return list(filter(lambda x: x.farmable, self.monsters))

    @property
    def desc(self):
        return self.desc_en or self.desc_ja

    @property
    def name(self):
        return self.name_en or self.name_ja


class DgLeaderSkill(DadguideItem):
    TABLE = 'leader_skills'
    PK = 'leader_skill_id'

    @property
    def data(self):
        return self.max_hp, self.max_atk, self.max_rcv, self.max_shield

    @property
    def desc(self):
        return self.desc_en or self.desc_ja

    @property
    def name(self):
        return self.name_en or self.name_ja


class DgAwakening(DadguideItem):
    TABLE = 'awakenings'
    PK = 'awakening_id'
    AS_BOOL = ['is_super']

    def __init__(self, item, database):
        super(DgAwakening, self).__init__(item, database)

    @property
    def skill(self):
        return self._database.get_awoken_skill(self.awoken_skill_id)

    @property
    def name(self):
        return self.skill.name_en if self.skill.name_en is not None else self.skill.name_ja


class DgAwokenSkill(DadguideItem):
    TABLE = 'awoken_skills'
    PK = 'awoken_skill_id'

    @property
    def monsters_with_awakening(self):
        return self._database.get_monsters_by_awakenings(self.awoken_skill_id)


class DgEvolution(DadguideItem):
    TABLE = 'evolutions'
    PK = 'evolution_id'

    def __init__(self, item, database):
        super(DgEvolution, self).__init__(item, database)
        self.evolution_type = EvoType(self.evolution_type)


class DgSeries(DadguideItem):
    TABLE = 'series'
    PK = 'series_id'

    @property
    def monsters(self):
        return self._database.get_monsters_by_series(self.series_id)

    @property
    def name(self):
        return self.name_en if self.name_en is not None else self.name_ja


class DgDungeon(DadguideItem):
    TABLE = 'dungeons'
    PK = 'dungeon_id'


class DgEncounter(DadguideItem):
    TABLE = 'encounters'
    PK = 'encounter_id'


class DgDrop(DadguideItem):
    TABLE = 'drops'
    PK = 'drop_id'


class DgScheduledEvent(DadguideItem):
    TABLE = 'schedule'
    PK = 'event_id'

    def __init__(self, item, database):
        super(DgScheduledEvent, self).__init__(item, database)
        self.dungeon = self._database.get_dungeon_by_id(self.dungeon_id)

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

    def __init__(self, item, database):
        super(DgMonster, self).__init__(item, database)

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

        self.awakenings = self._database.get_awakenings_by_monster(self.monster_id)
        self.superawakening_count = sum(int(a.is_super) for a in self.awakenings)

        self.is_inheritable = bool(self.inheritable)

        self.evo_from = self._database.get_prev_evolution_by_monster(self.monster_id)

        self.is_equip = any([x.awoken_skill_id == 49 for x in self.awakenings])

        base_id = self.monster_id
        next_base = self._database.get_prev_evolution_by_monster(base_id)
        while next_base is not None:
            base_id = next_base.from_id
            next_base = self._database.get_prev_evolution_by_monster(base_id)
        self._base_monster_id = base_id
        self._alt_evo_id_list = self._database.get_evolution_tree_ids(self._base_monster_id)

        self.search = MonsterSearchHelper(self)


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
        return self._database.get_active_skill(self.active_skill_id)

    @property
    def leader_skill(self):
        return self._database.get_leader_skill(self.leader_skill_id)

    @property
    def cur_evo_type(self):
        return self.evo_from.evolution_type if self.evo_from else EvoType.Base

    @property
    def true_evo_type(self):
        if self == self.base_monster:
            return InternalEvoType.Base
        elif 5077 in [dgi.monster_id for dgi in self.mats_for_evo]:
            return InternalEvoType.SuperReincarnated
        elif 3826 in [dgi.monster_id for dgi in self.mats_for_evo]:
            return InternalEvoType.Pixel
        elif self.is_equip:
            return InternalEvoType.Assist
        elif self.cur_evo_type == EvoType.UuvoReincarnated:
            return InternalEvoType.Reincarnated
        elif self.cur_evo_type == EvoType.UvoAwoken:
            return InternalEvoType.Ultimate
        else:
            return InternalEvoType.Normal

    @property
    def mats_for_evo(self):
        if self.evo_from is None:
            return []
        return [self._database.get_monster(self.evo_from['mat_{}_id'.format(i)]) for i in range(1, 6) if
                self.evo_from['mat_{}_id'.format(i)] is not None]

    @property
    def evo_gem(self):
        return self._database.get_monster_evo_gem(self.name_ja)

    @property
    def material_of(self):
        mat_of = self._database.get_evolution_by_material(self.monster_id)
        return [self._database.get_monster(x.to_id) for x in mat_of]

    def _evolutions_to(self):
        return self._database.get_next_evolutions_by_monster(self.monster_id)

    @property
    def evo_to(self):
        return [self._database.get_monster(x.to_id) for x in self._evolutions_to()]

    @property
    def base_monster(self):
        return self._database.get_monster(self._base_monster_id)

    @property
    def alt_evos(self):
        return [self._database.get_monster(a) for a in self._alt_evo_id_list]

    @property
    def is_base_monster(self):
        return self.evo_from is None

    @property
    def series(self):
        return self._database.get_series(self.series_id)

    @property
    def is_gfe(self):
        return self.series_id == 34

    @property
    def drop_dungeons(self):
        return self._database.get_drop_dungeons(self.monster_id)

    @property
    def farmable(self):
        return self._database.monster_is_farmable(self.monster_id)

    @property
    def farmable_evo(self):
        for e_id in self._alt_evo_id_list:
            if self._database.monster_is_farmable(e_id):
                return True
        return False

    @property
    def rem_evo(self):
        for e_id in self._alt_evo_id_list:
            if self._database.monster_in_rem(e_id):
                return True
        return False

    @property
    def pem_evo(self):
        for e_id in self._alt_evo_id_list:
            if self._database.monster_in_pem(e_id):
                return True
        return False

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
    def mp_evo(self):
        for e_id in self._alt_evo_id_list:
            if self._database.monster_in_mp_shop(e_id):
                return True
        return False

    @property
    def history_us(self):
        return '[{}] New Added'.format(self.reg_date)

    @property
    def next_monster(self):
        next = None
        offset = 1
        while next is None and self.monster_no + offset <= self._database._max_id():
            next = self._database.get_monster(self.monster_no + offset)
            offset += 1
        return next

    @property
    def prev_monster(self):
        next = None
        offset = 1
        while next is None and self.monster_no - offset >= 1:
            next = self._database.get_monster(self.monster_no - offset)
            offset += 1
        return next


class MonsterSearchHelper(object):
    def __init__(self, m: DgMonster):

        self.name = '{} {}'.format(m.name_en, m.name_ja).lower()
        leader_skill = m.leader_skill
        self.leader = leader_skill.desc.lower() if leader_skill else ''
        active_skill = m.active_skill
        self.active_name = active_skill.name.lower() if active_skill else ''
        self.active_desc = active_skill.desc.lower() if active_skill else ''
        self.active = '{} {}'.format(self.active_name, self.active_desc)
        self.active_min = active_skill.turn_min if active_skill else None
        self.active_max = active_skill.turn_max if active_skill else None

        self.color = [m.attr1.name.lower()]
        self.hascolor = [c.name.lower() for c in [m.attr1, m.attr2] if c]

        self.hp, self.atk, self.rcv, self.weighted_stats = m.stats(lv=110)

        self.types = [t.name for t in m.types]

        def replace_colors(text: str):
            return text.replace('red', 'fire').replace('blue', 'water').replace('green', 'wood')

        self.leader = replace_colors(self.leader)
        self.active = replace_colors(self.active)
        self.active_name = replace_colors(self.active_name)
        self.active_desc = replace_colors(self.active_desc)

        self.board_change = []
        self.orb_convert = defaultdict(list)
        self.row_convert = []
        self.column_convert = []

        def color_txt_to_list(txt):
            txt = txt.replace('and', ' ')
            txt = txt.replace(',', ' ')
            txt = txt.replace('orbs', ' ')
            txt = txt.replace('orb', ' ')
            txt = txt.replace('mortal poison', 'mortalpoison')
            txt = txt.replace('jammers', 'jammer')
            txt = txt.strip()
            return txt.split()

        def strip_prev_clause(txt: str, sep: str):
            prev_clause_start_idx = txt.find(sep)
            if prev_clause_start_idx >= 0:
                prev_clause_start_idx += len(sep)
                txt = txt[prev_clause_start_idx:]
            return txt

        def strip_next_clause(txt: str, sep: str):
            next_clause_start_idx = txt.find(sep)
            if next_clause_start_idx >= 0:
                txt = txt[:next_clause_start_idx]
            return txt

        active_desc = self.active_desc
        active_desc = active_desc.replace(' rows ', ' row ')
        active_desc = active_desc.replace(' columns ', ' column ')
        active_desc = active_desc.replace(' into ', ' to ')
        active_desc = active_desc.replace('changes orbs to', 'all orbs to')

        board_change_txt = 'all orbs to'
        if board_change_txt in active_desc:
            txt = strip_prev_clause(active_desc, board_change_txt)
            txt = strip_next_clause(txt, 'orbs')
            txt = strip_next_clause(txt, ';')
            self.board_change = color_txt_to_list(txt)

        txt = active_desc
        if 'row' in txt:
            parts = re.split(r'\Wand\W|;\W', txt)
            for i in range(0, len(parts)):
                if 'row' in parts[i]:
                    self.row_convert.append(strip_next_clause(
                        strip_prev_clause(parts[i], 'to '), ' orbs'))

        txt = active_desc
        if 'column' in txt:
            parts = re.split(r'\Wand\W|;\W', txt)
            for i in range(0, len(parts)):
                if 'column' in parts[i]:
                    self.column_convert.append(strip_next_clause(
                        strip_prev_clause(parts[i], 'to '), ' orbs'))

        convert_done = self.board_change or self.row_convert or self.column_convert

        change_txt = 'change '
        if not convert_done and change_txt in active_desc and 'orb' in active_desc:
            txt = active_desc
            parts = re.split(r'\Wand\W|;\W', txt)
            for i in range(0, len(parts)):
                parts[i] = strip_prev_clause(parts[i], change_txt) if change_txt in parts[i] else ''

            for part in parts:
                sub_parts = part.split(' to ')
                if len(sub_parts) > 1:
                    source_orbs = color_txt_to_list(sub_parts[0])
                    dest_orbs = color_txt_to_list(sub_parts[1])
                    for so in source_orbs:
                        for do in dest_orbs:
                            self.orb_convert[so].append(do)


def make_roma_subname(name_ja):
    subname = name_ja.replace('＝', '')
    adjusted_subname = ''
    for part in subname.split('・'):
        roma_part = romkan.to_roma(part)
        if part != roma_part and not tsutils.containsJa(roma_part):
            adjusted_subname += ' ' + roma_part.strip('-')
    return adjusted_subname.strip()


class MonsterIndex(tsutils.aobject):
    async def __init__(self, monster_database, nickname_overrides, basename_overrides,
                       panthname_overrides, accept_filter=None):
        # Important not to hold onto anything except IDs here so we don't leak memory
        base_monster_ids = monster_database.get_base_monster_ids()

        self.attr_short_prefix_map = {
            Attribute.Fire: ['r'],
            Attribute.Water: ['b'],
            Attribute.Wood: ['g'],
            Attribute.Light: ['l'],
            Attribute.Dark: ['d'],
            Attribute.Unknown: ['h'],
            Attribute.Nil: ['x'],
        }
        self.attr_long_prefix_map = {
            Attribute.Fire: ['red', 'fire'],
            Attribute.Water: ['blue', 'water'],
            Attribute.Wood: ['green', 'wood'],
            Attribute.Light: ['light'],
            Attribute.Dark: ['dark'],
            Attribute.Unknown: ['unknown'],
            Attribute.Nil: ['null', 'none'],
        }

        self.series_to_prefix_map = {
            130: ['halloween', 'hw', 'h'],
            136: ['xmas', 'christmas'],
            125: ['summer', 'beach'],
            114: ['school', 'academy', 'gakuen'],
            139: ['new years', 'ny'],
            149: ['wedding', 'bride'],
            154: ['padr'],
            175: ['valentines', 'vday', 'v'],
            183: ['gh', 'gungho'],
        }

        monster_id_to_nicknames = defaultdict(set)
        for monster_id, nicknames in nickname_overrides.items():
            monster_id_to_nicknames[monster_id] = nicknames

        named_monsters = []
        async for base_mon in AsyncIter(base_monster_ids):
            base_id = base_mon.monster_id
            group_basename_overrides = basename_overrides.get(base_id, [])
            evolution_tree = [monster_database.get_monster(m) for m in
                              monster_database.get_evolution_tree_ids(base_id)]
            named_mg = NamedMonsterGroup(evolution_tree, group_basename_overrides)
            for monster in evolution_tree:
                if accept_filter and not accept_filter(monster):
                    continue
                prefixes = self.compute_prefixes(monster, evolution_tree)
                extra_nicknames = monster_id_to_nicknames[monster.monster_id]
                named_monster = NamedMonster(monster, named_mg, prefixes, extra_nicknames)
                named_monsters.append(named_monster)

        # Sort the NamedMonsters into the opposite order we want to accept their nicknames in
        # This order is:
        #  1) High priority first
        #  2) Larger group sizes
        #  3) Minimum ID size in the group
        #  4) Monsters with higher ID values
        def named_monsters_sort(nm: NamedMonster):
            return (not nm.is_low_priority, nm.group_size, -1 *
                    nm.base_monster_no_na, nm.monster_no_na)

        named_monsters.sort(key=named_monsters_sort)

        # set up a set of all pantheon names, a set of all pantheon nicknames, and a dictionary of nickname -> full name
        # later we will set up a dictionary of pantheon full name -> monsters
        self.all_pantheon_names = set()
        self.all_pantheon_names.update(panthname_overrides.values())

        self.pantheon_nick_to_name = panthname_overrides
        self.pantheon_nick_to_name.update(panthname_overrides)

        self.all_pantheon_nicknames = set()
        self.all_pantheon_nicknames.update(panthname_overrides.keys())

        self.all_prefixes = set()
        self.pantheons = defaultdict(set)
        self.all_entries = {}
        self.two_word_entries = {}
        for nm in named_monsters:
            self.all_prefixes.update(nm.prefixes)
            for nickname in nm.final_nicknames:
                self.all_entries[nickname] = nm
            for nickname in nm.final_two_word_nicknames:
                self.two_word_entries[nickname] = nm
            if nm.series:
                for pantheon in self.all_pantheon_names:
                    if pantheon.lower() == nm.series.lower():
                        self.pantheons[pantheon.lower()].add(nm)

        self.all_monsters = named_monsters
        self.all_en_name_to_monsters = {m.name_en.lower(): m for m in named_monsters}
        self.monster_no_na_to_named_monster = {m.monster_no_na: m for m in named_monsters}
        self.monster_id_to_named_monster = {m.monster_id: m for m in named_monsters}

        for monster_id, nicknames in nickname_overrides.items():
            nm = self.monster_id_to_named_monster.get(monster_id)
            if nm:
                for nickname in nicknames:
                    self.all_entries[nickname] = nm

    def init_index(self):
        pass

    def compute_prefixes(self, m: DgMonster, evotree: list):
        prefixes = set()

        attr1_short_prefixes = self.attr_short_prefix_map[m.attr1]
        attr1_long_prefixes = self.attr_long_prefix_map[m.attr1]
        prefixes.update(attr1_short_prefixes)
        prefixes.update(attr1_long_prefixes)

        # If no 2nd attribute, use x so we can look those monsters up easier
        attr2_short_prefixes = self.attr_short_prefix_map.get(m.attr2, ['x'])
        for a1 in attr1_short_prefixes:
            for a2 in attr2_short_prefixes:
                prefixes.add(a1 + a2)
                prefixes.add(a1 + '/' + a2)

        # TODO: add prefixes based on type

        # Chibi monsters have the same NA name, except lowercased
        lower_name = m.name_en.lower()
        if m.name_en != m.name_ja:
            if lower_name == m.name_en:
                prefixes.add('chibi')
        elif 'ミニ' in m.name_ja:
            # Guarding this separately to prevent 'gemini' from triggering (e.g. 2645)
            prefixes.add('chibi')

        awoken = lower_name.startswith('awoken') or '覚醒' in lower_name
        revo = lower_name.startswith('reincarnated') or '転生' in lower_name
        srevo = lower_name.startswith('super reincarnated') or '超転生' in lower_name
        mega = lower_name.startswith('mega awoken') or '極醒' in lower_name
        awoken_or_revo_or_equip_or_mega = awoken or revo or m.is_equip or mega

        # These clauses need to be separate to handle things like 'Awoken Thoth' which are
        # actually Evos but have awoken in the name
        if awoken:
            prefixes.add('a')
            prefixes.add('awoken')

        if revo:
            prefixes.add('revo')
            prefixes.add('reincarnated')

        if mega:
            prefixes.add('mega')
            prefixes.add('mega awoken')
            prefixes.add('awoken')

        if srevo:
            prefixes.add('srevo')
            prefixes.add('super reincarnated')

        # Prefixes for evo type
        if m.cur_evo_type == EvoType.Base:
            prefixes.add('base')
        elif m.cur_evo_type == EvoType.Evo:
            prefixes.add('evo')
        elif m.cur_evo_type == EvoType.UvoAwoken and not awoken_or_revo_or_equip_or_mega:
            prefixes.add('uvo')
            prefixes.add('uevo')
        elif m.cur_evo_type == EvoType.UuvoReincarnated and not awoken_or_revo_or_equip_or_mega:
            prefixes.add('uuvo')
            prefixes.add('uuevo')

        if m.farmable:
            prefixes.add('farmable')

        # If any monster in the group is a pixel, add 'nonpixel' to all the versions
        # without pixel in the name. Add 'pixel' as a prefix to the ones with pixel in the name.
        def is_pixel(n):
            n = n.name_en.lower()
            return n.startswith('pixel') or n.startswith('ドット')

        for gm in evotree:
            if is_pixel(gm):
                prefixes.update(['pixel'] if is_pixel(m) else ['np', 'nonpixel'])
                break

        if m.is_equip:
            prefixes.add('assist')
            prefixes.add('equip')

        # Collab prefixes
        prefixes.update(self.series_to_prefix_map.get(m.series.series_id, []))

        return prefixes

    def find_monster(self, query):
        query = tsutils.rmdiacritics(query).lower().strip()

        # id search
        if query.isdigit():
            m = self.monster_no_na_to_named_monster.get(int(query))
            if m is None:
                return None, 'Looks like a monster ID but was not found', None
            else:
                return m, None, "ID lookup"
            # special handling for na/jp

        # TODO: need to handle na_only?

        # handle exact nickname match
        if query in self.all_entries:
            return self.all_entries[query], None, "Exact nickname"

        contains_ja = tsutils.containsJa(query)
        if len(query) < 2 and contains_ja:
            return None, 'Japanese queries must be at least 2 characters', None
        elif len(query) < 4 and not contains_ja:
            return None, 'Your query must be at least 4 letters', None

        # TODO: this should be a length-limited priority queue
        matches = set()

        # prefix search for ids, take max id
        for nickname, m in self.all_entries.items():
            if query.endswith("base {}".format(m.monster_id)):
                matches.add(
                    find_first(lambda mo: m.base_monster_no == mo.monster_id, self.all_entries.values()))
        if len(matches):
            return self.pickBestMonster(matches), None, "Base ID match, max of 1".format()

        # prefix search for nicknames, space-preceeded, take max id
        for nickname, m in self.all_entries.items():
            if nickname.startswith(query + ' '):
                matches.add(m)
        if len(matches):
            return self.pickBestMonster(matches), None, "Space nickname prefix, max of {}".format(len(matches))

        # prefix search for nicknames, take max id
        for nickname, m in self.all_entries.items():
            if nickname.startswith(query):
                matches.add(m)
        if len(matches):
            all_names = ",".join(map(lambda x: x.name_en, matches))
            return self.pickBestMonster(matches), None, "Nickname prefix, max of {}, matches=({})".format(
                len(matches), all_names)

        # prefix search for full name, take max id
        for nickname, m in self.all_entries.items():
            if (m.name_en.lower().startswith(query) or m.name_ja.lower().startswith(query)):
                matches.add(m)
        if len(matches):
            return self.pickBestMonster(matches), None, "Full name, max of {}".format(len(matches))

        # for nicknames with 2 names, prefix search 2nd word, take max id
        if query in self.two_word_entries:
            return self.two_word_entries[query], None, "Second-word nickname prefix, max of {}".format(len(matches))

        # TODO: refactor 2nd search characteristcs for 2nd word

        # full name contains on nickname, take max id
        for nickname, m in self.all_entries.items():
            if (query in m.name_en.lower() or query in m.name_ja.lower()):
                matches.add(m)
        if len(matches):
            return self.pickBestMonster(matches), None, 'Nickname contains nickname match ({})'.format(
                len(matches))

        # No decent matches. Try near hits on nickname instead
        matches = difflib.get_close_matches(query, self.all_entries.keys(), n=1, cutoff=.8)
        if len(matches):
            match = matches[0]
            return self.all_entries[match], None, 'Close nickname match ({})'.format(match)

        # Still no decent matches. Try near hits on full name instead
        matches = difflib.get_close_matches(
            query, self.all_en_name_to_monsters.keys(), n=1, cutoff=.9)
        if len(matches):
            match = matches[0]
            return self.all_en_name_to_monsters[match], None, 'Close name match ({})'.format(match)

        # About to give up, try matching all words
        matches = set()
        for nickname, m in self.all_entries.items():
            if (all(map(lambda x: x in m.name_en.lower(), query.split())) or
                    all(map(lambda x: x in m.name_ja.lower(), query.split()))):
                matches.add(m)
        if len(matches):
            return self.pickBestMonster(matches), None, 'All word match on full name, max of {}'.format(
                len(matches))

        # couldn't find anything
        return None, "Could not find a match for: " + query, None

    def find_monster2(self, query):
        """Search with alternative method for resolving prefixes.

        Implements the lookup for id2, where you are allowed to specify multiple prefixes for a card.
        All prefixes are required to be exactly matched by the card.
        Follows a similar logic to the regular id but after each check, will remove any potential match that doesn't
        contain every single specified prefix.
        """
        query = tsutils.rmdiacritics(query).lower().strip()
        # id search
        if query.isdigit():
            m = self.monster_no_na_to_named_monster.get(int(query))
            if m is None:
                return None, 'Looks like a monster ID but was not found', None
            else:
                return m, None, "ID lookup"

        # handle exact nickname match
        if query in self.all_entries:
            return self.all_entries[query], None, "Exact nickname"

        contains_ja = tsutils.containsJa(query)
        if len(query) < 2 and contains_ja:
            return None, 'Japanese queries must be at least 2 characters', None
        elif len(query) < 4 and not contains_ja:
            return None, 'Your query must be at least 4 letters', None

        # we want to look up only the main part of the query, and then verify that each result has the prefixes
        # so break up the query into an array of prefixes, and a string (new_query) that will be the lookup
        query_prefixes = []
        parts_of_query = query.split()
        new_query = ''
        for i, part in enumerate(parts_of_query):
            if part in self.all_prefixes:
                query_prefixes.append(part)
            else:
                new_query = ' '.join(parts_of_query[i:])
                break

        # if we don't have any prefixes, then default to using the regular id lookup
        if len(query_prefixes) < 1:
            return self.find_monster(query)

        matches = PotentialMatches()

        # prefix search for ids, take max id
        for nickname, m in self.all_entries.items():
            if query.endswith("base {}".format(m.monster_id)):
                matches.add(
                    find_first(lambda mo: m.base_monster_no == mo.monster_id, self.all_entries.values()))
        matches.remove_potential_matches_without_all_prefixes(query_prefixes)

        # first try to get matches from nicknames
        for nickname, m in self.all_entries.items():
            if new_query in nickname:
                matches.add(m)
        matches.remove_potential_matches_without_all_prefixes(query_prefixes)

        # if we don't have any candidates yet, pick a new method
        if not matches.length():
            # try matching on exact names next
            for nickname, m in self.all_en_name_to_monsters.items():
                if new_query in m.name_en.lower() or new_query in m.name_ja.lower():
                    matches.add(m)
            matches.remove_potential_matches_without_all_prefixes(query_prefixes)

        # check for exact match on pantheon name but only if needed
        if not matches.length():
            for pantheon in self.all_pantheon_nicknames:
                if new_query == pantheon.lower():
                    matches.get_monsters_from_potential_pantheon_match(pantheon, self.pantheon_nick_to_name,
                                                                       self.pantheons)
            matches.remove_potential_matches_without_all_prefixes(query_prefixes)

        # check for any match on pantheon name, again but only if needed
        if not matches.length():
            for pantheon in self.all_pantheon_nicknames:
                if new_query in pantheon.lower():
                    matches.get_monsters_from_potential_pantheon_match(pantheon, self.pantheon_nick_to_name,
                                                                       self.pantheons)
            matches.remove_potential_matches_without_all_prefixes(query_prefixes)

        if matches.length():
            return matches.pick_best_monster(), None, None
        return None, "Could not find a match for: " + query, None

    def pickBestMonster(self, named_monster_list):
        return max(named_monster_list, key=lambda x: (not x.is_low_priority, x.rarity, x.monster_no_na))


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
    def __init__(self, monster: DgMonster, monster_group: NamedMonsterGroup, prefixes: set, extra_nicknames: set):
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
        self.series = monster.series.name if monster.series else None

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
