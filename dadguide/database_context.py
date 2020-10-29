from datetime import datetime
from collections import OrderedDict, defaultdict, deque

from .database_manager import DadguideDatabase
from .monster_graph import MonsterGraph
from .database_manager import DgActiveSkill
from .database_manager import DgLeaderSkill
from .database_manager import DadguideItem
from .database_manager import DgMonster
from .database_manager import DgAwakening
from .database_manager import DgDungeon
from .database_manager import DgEncounter
from .database_manager import DgDrop
from .database_manager import DgEvolution
from .database_manager import DictWithAttrAccess
from .database_manager import DgScheduledEvent


class DbContext(object):
    def __init__(self, database: DadguideDatabase, graph: MonsterGraph):
        self.database = database
        self.graph = graph
        self.graph.set_database(self)
        self.cachedmonsters = None
        self.expiry = 0

        self.max_id = database._max_id()
        # self.generate_all_monsters()

    def generate_all_monsters(self):
        self.cachedmonsters = {m.monster_id: m for m in self.database.query_many(
            self.database.select_builder(tables={DgMonster.TABLE: DgMonster.FIELDS}),
            (),
            DgMonster,
            as_generator=True, db_context=self, graph=self.graph)}
        self.expiry = int(datetime.now().timestamp()) + 60 * 60

    def get_active_skill_query(self, active_skill_id: int):
        return self.database.select_one_entry_by_pk(
            active_skill_id, DgActiveSkill, db_context=self)

    def get_leader_skill_query(self, leader_skill_id: int):
        return self.database.select_one_entry_by_pk(
            leader_skill_id, DgLeaderSkill, db_context=self)

    def get_awoken_skill_ids(self):
        SELECT_AWOKEN_SKILL_IDS = 'SELECT awoken_skill_id from awoken_skills'
        return [r.awoken_skill_id for r in
                self.database.query_many(
                    SELECT_AWOKEN_SKILL_IDS, (), DadguideItem, as_generator=True,
                    db_context=self, graph=self.graph)]

    def get_monsters_by_awakenings(self, awoken_skill_id: int):
        # TODO: Make this not make monsters via query
        return self.database.query_many(
            self.database.select_builder(
                tables=OrderedDict({
                    DgMonster.TABLE: DgMonster.FIELDS,
                    DgAwakening.TABLE: None,
                }),
                where='{}.awoken_skill_id=?;'.format(DgAwakening.TABLE),
                key=('monster_id',),
                distinct=True
            ),
            (awoken_skill_id,),
            DgMonster, db_context=self, graph=self.graph)

    def get_drop_dungeons(self, monster_id):
        return self.database.query_many(
            self.database.select_builder(
                tables=OrderedDict({
                    DgDungeon.TABLE: DgDungeon.FIELDS,
                    DgEncounter.TABLE: None,
                    DgDrop.TABLE: None,
                }),
                where='{0}.monster_id=?'.format(DgDrop.TABLE),
                key=(DgDungeon.PK, DgEncounter.PK)
            ),
            (monster_id,),
            DgDungeon, db_context=self)

    def monster_is_farmable(self, monster_id):
        return self.database.query_one(
            self.database.select_builder(
                tables={DgDrop.TABLE: DgDrop.FIELDS},
                where='{0}.monster_id=?'.format(DgDrop.TABLE)
            ),
            (monster_id,),
            DgDrop, db_context=self) is not None

    def monster_in_rem(self, monster_id):
        m = self.get_monster(monster_id)
        return m is not None and m.rem_egg == 1

    def monster_in_pem(self, monster_id):
        m = self.get_monster(monster_id)
        return m is not None and m.pal_egg == 1

    def monster_in_mp_shop(self, monster_id):
        m = self.get_monster(monster_id)
        return m is not None and m.buy_mp is not None

    def get_prev_evolution_by_monster(self, monster_id):
        return self.graph.get_prev_evolution_by_monster_id(monster_id)

    def get_next_evolutions_by_monster(self, monster_id):
        return self.graph.get_next_evolutions_by_monster_id(monster_id)

    def get_base_monster_by_id(self, monster_id):
        return min(self.graph.get_alt_cards(monster_id))

    def get_evolution_by_material(self, monster_id):
        return self.database.query_many(
            self.database.select_builder(
                tables={DgEvolution.TABLE: DgEvolution.FIELDS},
                where=' OR '.join(['{}.mat_{}_id=?'.format(DgEvolution.TABLE, i) for i in range(1, 6)])
            ),
            (monster_id,) * 5,
            DgEvolution, db_context=self)

    def get_evolution_tree_ids(self, base_monster_id):
        # is not a tree i lied
        base_id = base_monster_id
        evolution_tree = [base_id]
        n_evos = deque()
        n_evos.append(base_id)
        while len(n_evos) > 0:
            n_evo_id = n_evos.popleft()
            for e in self.get_next_evolutions_by_monster(n_evo_id):
                n_evos.append(e)
                evolution_tree.append(e)
        return evolution_tree

    def get_monsters_where(self, f):
        return [m for m in self.get_all_monsters() if f(m)]

    def get_first_monster_where(self, f):
        ms = self.get_monsters_where(f)
        if ms:
            return min(ms, key=lambda m: m.monster_id)

    def get_monsters_by_series(self, series_id: int):
        return self.get_monsters_where(lambda m: m.series_id == series_id)

    def get_monsters_by_active(self, active_skill_id: int):
        return self.get_monsters_where(lambda m: m.active_skill_id == active_skill_id)

    def get_monster_evo_gem(self, name: str, region='ja'):
        gem_suffix = {
            'ja': 'の希石',
            'en': '\'s Gem',
            'ko': ' 의 휘석'
        }
        if region not in gem_suffix:
            return None
        gem_name = name + gem_suffix.get(region)
        return self.get_first_monster_where(
            lambda m: getattr(m, 'name_{}'.format(region)) == gem_name and m.leader_skill_id == 10628)

    def _get_monster_query(self, monster_id: int):
        monster = self.database.select_one_entry_by_pk(monster_id, DgMonster)
        if monster is not None:
            self.cachedmonsters[monster.monster_id] = monster
            return monster

    def get_monster(self, monster_id: int):
        self.refresh_monsters()
        if monster_id in self.cachedmonsters:
            return self.cachedmonsters.get(monster_id)
        return self._get_monster_query(monster_id)

    def get_all_monster_ids_query(self, as_generator=True):
        query = self.database.query_many(self.database.select_builder(tables={DgMonster.TABLE: ('monster_id',)}), (),
                                         DictWithAttrAccess,
                                         as_generator=as_generator,
                                         db_context=self, graph=self.graph)
        if as_generator:
            return map(lambda m: m.monster_id, query)
        return [m.monster_id for m in query]

    def refresh_monsters(self):
        if self.expiry < datetime.now().timestamp():
            self.generate_all_monsters()

    def get_all_monsters(self, as_generator=True):
        monsters = (self.get_monster(mid) for mid in self.get_all_monster_ids_query())
        if not as_generator:
            return [*monsters]
        return monsters

    def get_all_events(self, as_generator=True):
        return self.database.query_many(
            self.database.select_builder(tables={DgScheduledEvent.TABLE: DgScheduledEvent.FIELDS}), (),
            DgScheduledEvent, db_context=self,
            as_generator=as_generator)

    def get_dungeon_by_id(self, dungeon_id: int):
        return self.database.select_one_entry_by_pk(dungeon_id, DgDungeon)

    def get_base_monster_ids(self):
        SELECT_BASE_MONSTER_ID = '''
            SELECT evolutions.from_id as monster_id FROM evolutions WHERE evolutions.from_id NOT IN (SELECT DISTINCT evolutions.to_id FROM evolutions)
            UNION
            SELECT monsters.monster_id FROM monsters WHERE monsters.monster_id NOT IN (SELECT evolutions.from_id FROM evolutions UNION SELECT evolutions.to_id FROM evolutions)'''
        return self.database.query_many(
            SELECT_BASE_MONSTER_ID,
            (),
            DictWithAttrAccess, db_context=self,
            as_generator=True)

    def tokenize_monsters(self):
        tokens = defaultdict(list)
        for mid in self.get_all_monster_ids_query():
            monster = self.get_monster(mid)
            for token in monster.name_en.split():
                tokens[token.lower()].append(monster)
        return tokens

    def has_database(self):
        return self.database.has_database()

    def close(self):
        self.database.close()
