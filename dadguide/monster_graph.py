import networkx as nx
from collections import defaultdict
from .database_manager import DadguideDatabase
from .database_manager import DgActiveSkill
from .database_manager import DgLeaderSkill
from .database_manager import DgAwakening
from .database_manager import DictWithAttrAccess
from .database_manager import DgSeries


class MonsterGraph(object):
    def __init__(self, database: DadguideDatabase):
        self.database = database
        self.graph = None
        self._build_graph()
        self.graph: nx.DiGraph
        self.edges = self.graph.edges
        self.nodes = self.graph.nodes

    def _build_graph(self):
        self.graph = nx.DiGraph()

        ms = self.database.query_many("SELECT * FROM monsters", (), DictWithAttrAccess,
                                      graph=self)
        es = self.database.query_many("SELECT * FROM evolutions", (), DictWithAttrAccess,
                                      graph=self)
        aws = self.database.query_many("SELECT * FROM awakenings", (), DgAwakening,
                                       graph=self)
        lss = self.database.query_many("SELECT * FROM leader_skills", (), DgLeaderSkill, idx_key='leader_skill_id',
                                       graph=self)
        ass = self.database.query_many("SELECT * FROM active_skills", (), DgActiveSkill, idx_key='active_skill_id',
                                       graph=self)
        ss = self.database.query_many("SELECT * FROM series", (), DgSeries, idx_key='series_id',
                                      graph=self)

        mtoawo = defaultdict(list)
        for a in aws:
            mtoawo[a.monster_id].append(a)

        for m in ms:
            self.graph.add_node(m.monster_id,
                                awakenings=mtoawo[m.monster_id],
                                leader_skill=lss.get(m.leader_skill_id),
                                active_skill=ass.get(m.active_skill_id),
                                series=ss.get(m.series_id))
            if m.linked_monster_id:
                self.graph.add_edge(m.monster_id, m.linked_monster_id, type='transformation')
                self.graph.add_edge(m.linked_monster_id, m.monster_id, type='back_transformation')

        for e in es:
            self.graph.add_edge(e.from_id, e.to_id, type='evolution', **e)
            self.graph.add_edge(e.to_id, e.from_id, type='back_evolution', **e)
    
    @staticmethod
    def _get_edges(node, etype):
        return {mid for mid, edge in node.items() if edge.get('type') == etype}

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

    def get_prev_evolution_by_monster(self, monster_id):
        bes = self._get_edges(self.graph[monster_id], 'back_evolution')
        if bes: return bes.pop()

    def get_next_evolutions_by_monster(self, monster_id):
        return self._get_edges(self.graph[monster_id], 'evolution')
