import networkx as nx
from typing import Optional
from collections import defaultdict
from .database_manager import DgMonster
from .database_manager import DadguideDatabase
from .database_manager import DgAwakening
from .database_manager import DictWithAttrAccess
from .database_manager import EvoType
from .database_manager import InternalEvoType
from .models.monster_model import MonsterModel
from .models.leader_skill_model import LeaderSkillModel
from .models.active_skill_model import ActiveSkillModel
from .models.series_model import SeriesModel
from .models.evolution_model import EvolutionModel


class MonsterGraph(object):
    def __init__(self, database: DadguideDatabase):
        self.database = database
        self.graph = None
        self.graph: nx.DiGraph
        self.edges = None
        self.nodes = None
        self.max_monster_id = -1

    def build_graph(self):
        self.graph = nx.DiGraph()

        ms = self.database.query_many(
            "SELECT monsters.*, leader_skills.name_ja AS ls_name_ja, leader_skills.name_en AS ls_name_en, leader_skills.name_ko AS ls_name_ko, leader_skills.desc_ja AS ls_desc_ja, leader_skills.desc_en AS ls_desc_en, leader_skills.desc_ko AS ls_desc_ko, leader_skills.max_hp, leader_skills.max_atk, leader_skills.max_rcv, leader_skills.max_rcv, leader_skills.max_shield, leader_skills.max_combos, active_skills.name_ja AS as_name_ja, active_skills.name_en AS as_name_en, active_skills.name_ko AS as_name_ko, active_skills.desc_ja AS as_desc_ja, active_skills.desc_en AS as_desc_en, active_skills.desc_ko AS as_desc_ko, active_skills.turn_max, active_skills.turn_min, series.name_ja AS s_name_ja, series.name_en AS s_name_en, series.name_ko AS s_name_ko, exchanges.target_monster_id AS evo_gem_id, drops.drop_id FROM monsters LEFT OUTER JOIN leader_skills ON monsters.leader_skill_id = leader_skills.leader_skill_id LEFT OUTER JOIN active_skills ON monsters.active_skill_id = active_skills.active_skill_id LEFT OUTER JOIN series ON monsters.series_id = series.series_id LEFT OUTER JOIN exchanges on '(' || monsters.monster_id || ')' = exchanges.required_monster_ids LEFT OUTER JOIN drops ON monsters.monster_id = drops.monster_id GROUP BY monsters.monster_id", (), DictWithAttrAccess,
            graph=self)

        es = self.database.query_many("SELECT * FROM evolutions", (), DictWithAttrAccess,
                                      graph=self)

        aws = self.database.query_many("SELECT monster_id, awoken_skills.awoken_skill_id, is_super, order_idx, name_ja, name_en FROM awakenings JOIN awoken_skills ON awakenings.awoken_skill_id=awoken_skills.awoken_skill_id", (), DgAwakening,
                                       graph=self)

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
                                        desc_ja=m.as_desc_ja,
                                        desc_en=m.as_desc_en,
                                        desc_ko=m.as_desc_ko,
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
                                   series_id=m.series_id,
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
                                   buy_mp=m.buy_mp,
                                   sell_mp=m.sell_mp,
                                   sell_gold=m.sell_gold,
                                   reg_date=m.reg_date,
                                   on_jp=m.on_jp == 1,
                                   on_na=m.on_na == 1,
                                   on_kr=m.on_kr == 1,
                                   type_1_id=m.type_1_id,
                                   type_2_id=m.type_2_id,
                                   type_3_id=m.type_3_id,
                                   is_inheritable=m.inheritable == 1,
                                   evo_gem_id=m.evo_gem_id,
                                   orb_skin_id=m.orb_skin_id,
                                   cost=m.cost,
                                   level=m.level,
                                   exp=m.exp,
                                   limit_mult=m.limit_mult,
                                   pronunciation_ja=m.pronunciation_ja,
                                   hp_max=m.hp_max,
                                   hp_min=m.hp_min,
                                   hp_scale=m.hp_scale,
                                   atk_max=m.atk_max,
                                   atk_min=m.atk_min,
                                   atk_scale=m.atk_scale,
                                   rcv_max=m.rcv_max,
                                   rcv_min=m.rcv_min,
                                   rcv_scale=m.rcv_scale,
                                   latent_slots=m.latent_slots,
                                   has_animation=m.has_animation == 1,
                                   has_hqimage=m.has_hqimage == 1
                                   )

            self.graph.add_node(m.monster_id, model=m_model)
            if m.linked_monster_id:
                self.graph.add_edge(m.monster_id, m.linked_monster_id, type='transformation')
                self.graph.add_edge(m.linked_monster_id, m.monster_id, type='back_transformation')

            self.max_monster_id = max(self.max_monster_id, m.monster_id)

        for e in es:
            evo_model = EvolutionModel(**e)
            self.graph.add_edge(e.from_id, e.to_id, type='evolution', model=evo_model)
            self.graph.add_edge(e.to_id, e.from_id, type='back_evolution', model=evo_model)

        self.edges = self.graph.edges
        self.nodes = self.graph.nodes

    @staticmethod
    def _get_edges(node, etype):
        return {mid for mid, edge in node.items() if edge.get('type') == etype}

    @staticmethod
    def _get_edge_model(node, etype):
        possible_results = set()
        for _, edge in node.items():
            if edge.get('type') == etype:
                possible_results.add(edge['model'])
        if len(possible_results) == 0:
            return None
        return sorted(possible_results, key=lambda x: x.tstamp)[-1]

    def get_monster(self, monster_id) -> Optional[MonsterModel]:
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

    def monster_is_base_by_id(self, monster_id: int) -> bool:
        return self.get_base_id_by_id(monster_id) == monster_id

    def monster_is_base(self, monster: DgMonster) -> bool:
        return self.monster_is_base_by_id(monster.monster_no)

    def get_numerical_sort_top_id_by_id(self, monster_id):
        alt_cards = self.get_alt_cards(monster_id)
        if alt_cards is None:
            return None
        return sorted(alt_cards)[-1]

    def get_numerical_sort_top_monster_by_id(self, monster_id):
        return self.get_monster(self.get_numerical_sort_top_id_by_id(monster_id))

    def get_evo_by_monster_id(self, monster_id) -> Optional[EvolutionModel]:
        return self._get_edge_model(self.graph[monster_id], 'back_evolution')
        # prev_evo = self.get_prev_evolution_by_monster_id(monster_id)
        # if prev_evo is None:
        #     return None
        # return self.graph.edges[prev_evo, monster_id]['model']

    def cur_evo_type_by_monster_id(self, monster_id: int) -> EvoType:
        prev_evo = self.get_evo_by_monster_id(monster_id)
        return EvoType(prev_evo.evolution_type) if prev_evo else EvoType.Base

    def cur_evo_type_by_monster(self, monster: DgMonster) -> EvoType:
        return self.cur_evo_type_by_monster_id(monster.monster_no)

    def true_evo_type_by_monster_id(self, monster_id: int) -> InternalEvoType:
        if self.get_base_id_by_id(monster_id) == monster_id:
            return InternalEvoType.Base

        evo = self.get_evo_by_monster_id(monster_id)
        if evo is None:
            # this is possible without being the above case for transforms
            return InternalEvoType.Base
        if evo.is_super_reincarnated:
            return InternalEvoType.SuperReincarnated
        elif evo.is_pixel:
            return InternalEvoType.Pixel

        monster = self.get_monster(monster_id)
        if monster.is_equip:
            return InternalEvoType.Assist

        cur_evo_type = self.cur_evo_type_by_monster_id(monster_id)
        if cur_evo_type == EvoType.UuvoReincarnated:
            return InternalEvoType.Reincarnated
        elif cur_evo_type == EvoType.UvoAwoken:
            return InternalEvoType.Ultimate

        return InternalEvoType.Normal

    def true_evo_type_by_monster(self, monster: DgMonster) -> InternalEvoType:
        return self.true_evo_type_by_monster_id(monster.monster_no)

    def get_prev_evolution_by_monster_id(self, monster_id):
        bes = self._get_edges(self.graph[monster_id], 'back_evolution')
        if bes:
            return bes.pop()
        return None

    def get_prev_evolution_by_monster(self, monster: DgMonster):
        return self.get_prev_evolution_by_monster_id(monster.monster_no)

    def get_next_evolutions_by_monster_id(self, monster_id):
        return self._get_edges(self.graph[monster_id], 'evolution')

    def evo_mats_by_monster_id(self, monster_id: int) -> list:
        evo = self.get_evo_by_monster_id(monster_id)
        if evo is None:
            return []
        return [self.get_monster(mat) for mat in evo.mats]

    def evo_mats_by_monster(self, monster: DgMonster) -> list:
        return self.evo_mats_by_monster_id(monster.monster_no)

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

    def next_monster_id_by_id(self, monster_id: int) -> Optional[int]:
        next_monster = None
        offset = 1
        while next_monster is None and monster_id + offset <= self.max_monster_id:
            next_monster = self.get_monster(monster_id + offset)
            offset += 1
        if next_monster is None:
            return None
        return next_monster.monster_id

    def prev_monster_id_by_id(self, monster_id) -> Optional[int]:
        prev_monster = None
        offset = 1
        while prev_monster is None and monster_id - offset >= 1:
            prev_monster = self.get_monster(monster_id - offset)
            offset += 1
        if prev_monster is None:
            return None
        return prev_monster.monster_id

    def evo_gem_monster_by_id(self, monster_id) -> Optional[MonsterModel]:
        this_monster = self.get_monster(monster_id)
        if this_monster.evo_gem_id is None:
            return None
        return self.get_monster(this_monster.evo_gem_id)

    def evo_gem_monster(self, monster: DgMonster) -> Optional[MonsterModel]:
        return self.evo_gem_monster_by_id(monster.monster_no)
