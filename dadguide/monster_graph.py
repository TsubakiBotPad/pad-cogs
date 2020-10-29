import networkx as nx
from collections import defaultdict
from .database_manager import DgMonster
from .database_manager import DadguideDatabase
from .database_manager import DgAwakening
from .database_manager import DictWithAttrAccess
from .models.monster_model import MonsterModel
from .models.leader_skill_model import LeaderSkillModel
from .models.active_skill_model import ActiveSkillModel
from .models.series_model import SeriesModel


class MonsterGraph(object):
    def __init__(self, database: DadguideDatabase):
        self.database = database
        self.db_context = None
        self.graph = None
        self.graph: nx.DiGraph
        self.edges = None
        self.nodes = None

    def set_database(self, db_context):
        self.db_context = db_context

    def build_graph(self):
        self.graph = nx.DiGraph()

        ms = self.database.query_many(
            "SELECT monsters.*, leader_skills.name_ja AS ls_name_ja, leader_skills.name_en AS ls_name_en, leader_skills.name_ko AS ls_name_ko, leader_skills.desc_ja AS ls_desc_ja, leader_skills.desc_en AS ls_desc_en, leader_skills.desc_ko AS ls_desc_ko, leader_skills.max_hp, leader_skills.max_atk, leader_skills.max_rcv, leader_skills.max_rcv, leader_skills.max_shield, leader_skills.max_combos, active_skills.name_ja AS as_name_ja, active_skills.name_en AS as_name_en, active_skills.name_ko AS as_name_ko, active_skills.desc_ja AS as_desc_ja, active_skills.desc_en AS as_desc_en, active_skills.desc_ko AS as_desc_ko, active_skills.turn_max, active_skills.turn_min, series.name_ja AS s_name_ja, series.name_en AS s_name_en, series.name_ko AS s_name_ko, drops.drop_id FROM monsters LEFT OUTER JOIN leader_skills ON monsters.leader_skill_id = leader_skills.leader_skill_id LEFT OUTER JOIN active_skills ON monsters.active_skill_id = active_skills.active_skill_id LEFT OUTER JOIN series ON monsters.series_id = series.series_id LEFT OUTER JOIN drops ON monsters.monster_id = drops.monster_id GROUP BY monsters.monster_id", (), DictWithAttrAccess,
            db_context=self.db_context, graph=self)

        es = self.database.query_many("SELECT * FROM evolutions", (), DictWithAttrAccess,
                                      db_context=self.db_context, graph=self)

        aws = self.database.query_many("SELECT monster_id, awoken_skills.awoken_skill_id, is_super, order_idx, name_ja, name_en FROM awakenings JOIN awoken_skills ON awakenings.awoken_skill_id=awoken_skills.awoken_skill_id", (), DgAwakening,
                                       db_context=self.db_context, graph=self)

        mtoawo = defaultdict(list)
        for a in aws:
            mtoawo[a.monster_id].append(a)

        for m in ms:
            ls_model = LeaderSkillModel(leader_skill_id=m.leader_skill_id,
                                        name_ja=m.ls_name_ja,
                                        name_en=m.ls_name_en,
                                        name_ko=m.ls_name_ko,
                                        desc_ja=m.ls_desc_ja,
                                        desc_en=m.ls_desc_en,
                                        desc_ko=m.ls_desc_ko,
                                        max_hp=m.max_hp,
                                        max_atk=m.max_atk,
                                        max_rcv=m.max_rcv,
                                        max_shield=m.max_shield,
                                        max_combos=m.max_combos
                                        ) if m.leader_skill_id != 0 else None

            as_model = ActiveSkillModel(active_skill_id=m.active_skill_id,
                                        name_ja=m.as_name_ja,
                                        name_en=m.as_name_en,
                                        name_ko=m.as_name_ko,
                                        desc_ja=m.as_name_ja,
                                        desc_en=m.as_name_en,
                                        desc_ko=m.as_name_ko,
                                        turn_max=m.turn_max,
                                        turn_min=m.turn_min
                                        ) if m.active_skill_id != 0 else None

            s_model = SeriesModel(series_id=m.series_id,
                                  name_ja=m.s_name_ja,
                                  name_en=m.s_name_en,
                                  name_ko=m.s_name_ko
                                  )

            m_model = MonsterModel(monster_id=m.monster_id,
                                   monster_no_jp=m.monster_no_jp,
                                   monster_no_na=m.monster_no_na,
                                   monster_no_kr=m.monster_no_kr,
                                   awakenings=mtoawo[m.monster_id],
                                   leader_skill=ls_model,
                                   active_skill=as_model,
                                   series=s_model,
                                   attribute_1_id=m.attribute_1_id,
                                   attribute_2_id=m.attribute_2_id,
                                   name_ja=m.name_ja,
                                   name_en=m.name_en,
                                   name_ko=m.name_ko,
                                   name_en_override=m.name_en_override,
                                   rarity=m.rarity,
                                   is_farmable=m.drop_id is not None,
                                   in_pem=m.pal_egg == 1,
                                   in_rem=m.rem_egg == 1,
                                   in_mpshop=m.buy_mp is not None,
                                   on_jp=m.on_jp == 1,
                                   on_na=m.on_na == 1,
                                   on_kr=m.on_kr == 1,
                                   type_1_id=m.type_1_id,
                                   type_2_id=m.type_2_id,
                                   type_3_id=m.type_3_id
                                   )

            self.graph.add_node(m.monster_id, model=m_model)
            if m.linked_monster_id:
                self.graph.add_edge(m.monster_id, m.linked_monster_id, type='transformation')
                self.graph.add_edge(m.linked_monster_id, m.monster_id, type='back_transformation')

        for e in es:
            self.graph.add_edge(e.from_id, e.to_id, type='evolution', **e)
            self.graph.add_edge(e.to_id, e.from_id, type='back_evolution', **e)

        self.edges = self.graph.edges
        self.nodes = self.graph.nodes

    @staticmethod
    def _get_edges(node, etype):
        return {mid for mid, edge in node.items() if edge.get('type') == etype}

    def get_monster(self, monster_id):
        if monster_id not in self.graph.nodes:
            return None
        return self.graph.nodes[monster_id]['model']

    def get_evo_tree(self, monster_id):
        ids = set()
        to_check = {monster_id}
        while to_check:
            mid = to_check.pop()
            if mid in ids:
                continue
            n = self.graph[mid]
            to_check.update(self._get_edges(n, 'evolution'))
            to_check.update(self._get_edges(n, 'back_evolution'))
            ids.add(mid)
        return ids

    def get_transform_tree(self, monster_id):
        ids = set()
        to_check = {monster_id}
        while to_check:
            mid = to_check.pop()
            if mid in ids:
                continue
            n = self.graph[mid]
            to_check.update(self._get_edges(n, 'transformation'))
            to_check.update(self._get_edges(n, 'back_transformation'))
            ids.add(mid)
        return ids

    def get_alt_cards(self, monster_id):
        ids = set()
        to_check = {monster_id}
        while to_check:
            mid = to_check.pop()
            if mid in ids:
                continue
            n = self.graph[mid]
            to_check.update(self._get_edges(n, 'evolution'))
            to_check.update(self._get_edges(n, 'transformation'))
            to_check.update(self._get_edges(n, 'back_evolution'))
            to_check.update(self._get_edges(n, 'back_transformation'))
            ids.add(mid)
        return ids

    def get_alt_monsters_by_id(self, monster_id):
        ids = self.get_alt_cards(monster_id)
        return [self.get_monster(m_id) for m_id in ids]

    def get_base_id_by_id(self, monster_id):
        alt_cards = self.get_alt_cards(monster_id)
        if alt_cards is None:
            return None
        return sorted(alt_cards)[0]

    def get_base_monster_by_id(self, monster_id):
        return self.get_monster(self.get_base_id_by_id(monster_id))

    def get_prev_evolution_by_monster_id(self, monster_id):
        bes = self._get_edges(self.graph[monster_id], 'back_evolution')
        if bes: return bes.pop()

    def get_next_evolutions_by_monster_id(self, monster_id):
        return self._get_edges(self.graph[monster_id], 'evolution')

    # farmable
    def monster_is_farmable_by_id(self, monster_id):
        return self.graph.nodes[monster_id]['model'].is_farmable

    def monster_is_farmable(self, monster: DgMonster):
        return self.monster_is_farmable_by_id(monster.monster_no)

    def monster_is_farmable_evo_by_id(self, monster_id):
        return any(
            m for m in self.get_evo_tree(monster_id) if self.monster_is_farmable_by_id(m))

    def monster_is_farmable_evo(self, monster: DgMonster):
        return self.monster_is_farmable_evo_by_id(monster.monster_no)

    # mp
    def monster_is_mp_by_id(self, monster_id):
        return self.graph.nodes[monster_id]['model'].in_mpshop

    def monster_is_mp(self, monster: DgMonster):
        return self.monster_is_mp_by_id(monster.monster_no)

    def monster_is_mp_evo_by_id(self, monster_id):
        return any(
            m for m in self.get_evo_tree(monster_id) if self.monster_is_mp_by_id(m))

    def monster_is_mp_evo(self, monster: DgMonster):
        return self.monster_is_mp_evo_by_id(monster.monster_no)

    # pem
    def monster_is_pem_by_id(self, monster_id):
        return self.graph.nodes[monster_id]['model'].in_pem

    def monster_is_pem(self, monster: DgMonster):
        return self.monster_is_pem_by_id(monster.monster_no)

    def monster_is_pem_evo_by_id(self, monster_id):
        return any(
            m for m in self.get_evo_tree(monster_id) if self.monster_is_pem_by_id(m))

    def monster_is_pem_evo(self, monster: DgMonster):
        return self.monster_is_pem_evo_by_id(monster.monster_no)

    # rem
    def monster_is_rem_by_id(self, monster_id):
        return self.graph.nodes[monster_id]['model'].in_rem

    def monster_is_rem(self, monster: DgMonster):
        return self.monster_is_rem_by_id(monster.monster_no)

    def monster_is_rem_evo_by_id(self, monster_id):
        return any(
            m for m in self.get_evo_tree(monster_id) if self.monster_is_rem_by_id(m))

    def monster_is_rem_evo(self, monster: DgMonster):
        return self.monster_is_rem_evo_by_id(monster.monster_no)
