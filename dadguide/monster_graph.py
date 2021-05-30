import json
import re
from collections import defaultdict
from typing import Optional, List, Union, Set

from networkx import MultiDiGraph
from networkx.classes.coreviews import AtlasView

from .common.enums import DEFAULT_SERVER, Server
from .database_manager import DadguideDatabase
from .models.active_skill_model import ActiveSkillModel
from .models.awakening_model import AwakeningModel
from .models.awoken_skill_model import AwokenSkillModel
from .models.enum_types import InternalEvoType
from .models.evolution_model import EvolutionModel
from .models.leader_skill_model import LeaderSkillModel
from .models.monster_model import MonsterModel, MonsterDifference
from .models.series_model import SeriesModel

MONSTER_QUERY = """SELECT
  monsters{0}.*,
  COALESCE(monster_name_overrides.name_en, monsters{0}.name_en_override) AS name_en_override,
  leader_skills{0}.name_ja AS ls_name_ja,
  leader_skills{0}.name_en AS ls_name_en,
  leader_skills{0}.name_ko AS ls_name_ko,
  leader_skills{0}.desc_ja AS ls_desc_ja,
  leader_skills{0}.desc_en AS ls_desc_en,
  leader_skills{0}.desc_ko AS ls_desc_ko,
  leader_skills{0}.max_hp,
  leader_skills{0}.max_atk,
  leader_skills{0}.max_rcv,
  leader_skills{0}.max_rcv,
  leader_skills{0}.max_shield,
  leader_skills{0}.max_combos,
  leader_skills{0}.bonus_damage,
  leader_skills{0}.mult_bonus_damage,
  leader_skills{0}.extra_time,
  active_skills{0}.name_ja AS as_name_ja,
  active_skills{0}.name_en AS as_name_en,
  active_skills{0}.name_ko AS as_name_ko,
  active_skills{0}.desc_ja AS as_desc_ja,
  active_skills{0}.desc_en AS as_desc_en,
  active_skills{0}.desc_ko AS as_desc_ko,
  active_skills{0}.turn_max,
  active_skills{0}.turn_min,
  series.name_ja AS s_name_ja,
  series.name_en AS s_name_en,
  series.name_ko AS s_name_ko,
  series.series_type AS s_series_type,
  exchanges.target_monster_id AS evo_gem_id,
  drops.drop_id
FROM
  monsters{0}
  LEFT OUTER JOIN leader_skills{0} ON monsters{0}.leader_skill_id = leader_skills{0}.leader_skill_id
  LEFT OUTER JOIN active_skills{0} ON monsters{0}.active_skill_id = active_skills{0}.active_skill_id
  LEFT OUTER JOIN series ON monsters{0}.series_id = series.series_id
  LEFT OUTER JOIN monsters{0} AS target_monsters ON monsters{0}.name_ja || 'の希石' = target_monsters.name_ja
  LEFT OUTER JOIN exchanges ON target_monsters.monster_id = exchanges.target_monster_id
  LEFT OUTER JOIN drops ON monsters{0}.monster_id = drops.monster_id
  LEFT OUTER JOIN monster_name_overrides ON monsters{0}.monster_id = monster_name_overrides.monster_id
GROUP BY
  monsters{0}.monster_id"""

# make sure we're only looking at the most recent row for any evolution
# since the database might have old data in it still
# group by `to_id` and not `evolution_id` because PAD monsters can only have 1 recipe, and
# the evolution_id changes when data changes so grouping by evolution_id is unhelpful
EVOS_QUERY = """SELECT
  evolutions{0}.*
FROM
  (
    SELECT
      evolution_id,
      MAX(tstamp) AS tstamp
    FROM
      evolutions{0}
    GROUP BY
      to_id
  ) AS latest_evolutions
  INNER JOIN evolutions{0} ON evolutions{0}.evolution_id = latest_evolutions.evolution_id
  AND evolutions{0}.tstamp = latest_evolutions.tstamp"""

AWAKENINGS_QUERY = """SELECT
  awakenings{0}.awakening_id,
  awakenings{0}.monster_id,
  awakenings{0}.is_super,
  awakenings{0}.order_idx,
  awoken_skills.*
FROM
  awakenings{0}
  JOIN awoken_skills ON awakenings{0}.awoken_skill_id = awoken_skills.awoken_skill_id"""

EGG_QUERY = """SELECT
   d_egg_machine_types.name AS type,
   egg_machines.*
FROM
  egg_machines
  JOIN d_egg_machine_types ON d_egg_machine_types.egg_machine_type_id = egg_machines.egg_machine_type_id
"""

EXCHANGE_QUERY = """SELECT
   *
FROM
  exchanges
"""

SPECIFY_SERVER = " WHERE server_id = {}"


class MonsterGraph(object):
    def __init__(self, database: DadguideDatabase):
        self.database = database
        self.max_monster_id = -1
        self.graph_dict = {
            "COMBINED": self.build_graph("COMBINED"),
            "NA": self.build_graph("NA"),
        }

        for server in self.graph_dict:
            self._cache_graph(server)

    def build_graph(self, server: Server) -> MultiDiGraph:
        graph = MultiDiGraph()

        table_suffix = ""
        where = ""
        if server != "COMBINED":
            table_suffix = "_" + server.lower()
            where = SPECIFY_SERVER.format(["JP", "NA", "KR"].index(server))

        ms = self.database.query_many(MONSTER_QUERY.format(table_suffix), ())
        es = self.database.query_many(EVOS_QUERY.format(table_suffix), ())
        aws = self.database.query_many(AWAKENINGS_QUERY.format(table_suffix), ())
        ems = self.database.query_many(EGG_QUERY.format(table_suffix) + where, ())
        exs = self.database.query_many(EXCHANGE_QUERY.format(table_suffix) + where, ())

        mtoawo = defaultdict(list)
        for a in aws:
            awoken_skill_model = AwokenSkillModel(**a)
            awakening_model = AwakeningModel(awoken_skill_model=awoken_skill_model, **a)
            mtoawo[a.monster_id].append(awakening_model)

        mtoegg = defaultdict(lambda: {'pem': False, 'rem': False})
        for e in ems:
            data = json.loads(e.contents)
            e_type = 'pem' if e.type == "PEM" else 'rem'
            for m in data:
                idx = int(m[1:-1])  # Remove parentheses
                mtoegg[idx][e_type] = True

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
                                        max_combos=m.max_combos,
                                        bonus_damage=m.bonus_damage,
                                        mult_bonus_damage=m.mult_bonus_damage,
                                        extra_time=m.extra_time,
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
                                  name_ko=m.s_name_ko,
                                  series_type=m.s_series_type
                                  )

            m_model = MonsterModel(monster_id=m.monster_id,
                                   base_evo_id=m.base_id,
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
                                   in_pem=mtoegg[m.monster_id]['pem'],
                                   in_rem=mtoegg[m.monster_id]['rem'],
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
                                   is_stackable=m.stackable == 1,
                                   evo_gem_id=m.evo_gem_id,
                                   orb_skin_id=m.orb_skin_id,
                                   cost=m.cost,
                                   level=m.level,
                                   exp=m.exp,
                                   fodder_exp=m.fodder_exp,
                                   limit_mult=m.limit_mult,
                                   pronunciation_ja=m.pronunciation_ja,
                                   voice_id_jp=m.voice_id_jp,
                                   voice_id_na=m.voice_id_na,
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
                                   has_hqimage=m.has_hqimage == 1,
                                   server_priority=server,
                                   )

            graph.add_node(m.monster_id, model=m_model)
            if m.linked_monster_id:
                graph.add_edge(m.monster_id, m.linked_monster_id, type='transformation')
                graph.add_edge(m.linked_monster_id, m.monster_id, type='back_transformation')

            if m.evo_gem_id:
                graph.add_edge(m.monster_id, m.evo_gem_id, type='evo_gem_from')
                graph.add_edge(m.evo_gem_id, m.monster_id, type='evo_gem_of')

            self.max_monster_id = max(self.max_monster_id, m.monster_id)

        for e in es:
            evo_model = EvolutionModel(**e)

            graph.add_edge(
                evo_model.from_id, evo_model.to_id, type='evolution', model=evo_model)
            graph.add_edge(
                evo_model.to_id, evo_model.from_id, type='back_evolution', model=evo_model)

            # for material_of queries
            already_used_in_this_evo = []  # don't add same mat more than once per evo
            for mat in evo_model.mats:
                if mat in already_used_in_this_evo:
                    continue
                graph.add_edge(
                    mat, evo_model.to_id, type="material_of", model=evo_model)
                already_used_in_this_evo.append(mat)

        for ex in exs:
            for vendor_id in re.findall(r'\d+', ex.required_monster_ids):
                graph.add_edge(
                    ex.target_monster_id, int(vendor_id), type='exchange_from')
                graph.add_edge(
                    int(vendor_id), ex.target_monster_id, type='exchange_for')

        return graph

    def _cache_graph(self, server: str):
        for mid in self.graph_dict[server].nodes:
            self.graph_dict[server].nodes[mid]['alt_versions'] = self.process_alt_versions(mid, server)

    def _get_edges(self, node: Union[int, AtlasView], etype, server: Server = DEFAULT_SERVER) -> Set[int]:
        if isinstance(node, int):
            node = self.graph_dict[server][node]

        return {mid for mid, atlas in node.items() for edge in atlas.values() if edge.get('type') == etype}

    def _get_edge_or_none(self, node: Union[int, AtlasView], etype, server: Server = DEFAULT_SERVER) -> Optional[int]:
        edges = self._get_edges(node, etype, server)
        if edges:
            return edges.pop()

    def _get_edge_model(self, node: Union[int, AtlasView], etype, server: Server = DEFAULT_SERVER):
        if isinstance(node, int):
            node = self.graph_dict[server][node]

        possible_results = set()
        for atlas in node.values():
            for edge in atlas.values():
                if edge.get('type') == etype:
                    possible_results.add(edge['model'])
        if len(possible_results) == 0:
            return None
        return sorted(possible_results, key=lambda x: x.tstamp)[-1]

    def get_monster(self, monster_id: int, server: Server = DEFAULT_SERVER) -> Optional[MonsterModel]:
        if monster_id not in self.graph_dict[server].nodes:
            return None
        return self.graph_dict[server].nodes[monster_id]['model']

    def get_all_monsters(self, server: Server = DEFAULT_SERVER) -> Set[MonsterModel]:
        return {mdata['model'] for mdata in self.graph_dict[server].nodes.values()}

    def get_evo_tree(self, monster_id, server: Server = DEFAULT_SERVER) -> List[int]:
        while (prev := self._get_edges(monster_id, 'back_evolution', server)):
            monster_id = prev
        return self.get_evo_tree_from_base(monster_id, server)

    def get_evo_tree_from_base(self, base_monster_id, server: Server = DEFAULT_SERVER) -> List[int]:
        ids = [base_monster_id]
        for evo in sorted(self._get_edges(base_monster_id, 'evolution', server)):
            ids += self.get_evo_tree_from_base(evo, server)
        return ids

    def get_transform_tree(self, monster_id: int, server: Server = DEFAULT_SERVER):
        ids = set()
        to_check = {monster_id}
        while to_check:
            mid = to_check.pop()
            if mid in ids:
                continue
            to_check.update(self._get_edges(mid, 'transformation', server))
            to_check.update(self._get_edges(mid, 'back_transformation', server))
            ids.add(mid)
        return ids

    def get_transform_monsters(self, monster: MonsterModel):
        return {self.get_monster(mid, monster.server_priority)
                for mid in self.get_transform_tree(monster.monster_id, monster.server_priority)}

    def process_alt_versions(self, monster_id, server) -> List[int]:
        return self.process_alt_versions_from_base(self.get_base_id_by_id(monster_id, server), server)

    def process_alt_versions_from_base(self, base_monster_id, server: Server = DEFAULT_SERVER) -> List[int]:
        ids = [base_monster_id]
        for trans in sorted(self._get_edges(base_monster_id, 'transformation', server)):
            if trans > base_monster_id or trans == 5802:  # I hate DMG very much
                ids += self.process_alt_versions_from_base(trans, server)
        for evo in sorted(self._get_edges(base_monster_id, 'evolution', server)):
            ids += self.process_alt_versions_from_base(evo, server)
        return ids

    def get_alt_ids_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self.graph_dict[server].nodes[monster_id]['alt_versions']

    def get_alt_ids(self, monster: MonsterModel):
        return self.get_alt_ids_by_id(monster.monster_id, monster.server_priority)

    def get_alt_monsters_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        ids = self.get_alt_ids_by_id(monster_id, server)
        return [self.get_monster(m_id, server) for m_id in ids]

    def get_alt_monsters(self, monster: MonsterModel):
        return self.get_alt_monsters_by_id(monster.monster_id, monster.server_priority)

    def get_base_id_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self.get_base_id(self.get_monster(monster_id, server))

    def get_base_id(self, monster):
        # This fixes DMG.  I *hate* DMG.
        if monster.base_evo_id == 5802:
            return 5810

        while (prevs := self.get_prev_transforms_by_monster(monster)) \
                and list(prevs)[0].monster_id < monster.monster_id:
            monster = prevs.pop()

        return monster.base_evo_id

    def get_base_monster_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self.get_monster(self.get_base_id_by_id(monster_id, server), server)

    def get_base_monster(self, monster: MonsterModel):
        return self.get_monster(self.get_base_id(monster), monster.server_priority)

    def monster_is_base_by_id(self, monster_id: int, server: Server = DEFAULT_SERVER) -> bool:
        return self.monster_is_base(self.get_monster(monster_id, server))

    def monster_is_base(self, monster: MonsterModel) -> bool:
        return self.get_base_id(monster) == monster.monster_id

    def get_transform_base_id_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        # NOTE: This assumes that no two monsters will transform to the same monster. This
        #        also doesn't work for monsters like DMG which are transforms but also base
        #        cards.  This also assumes that the "base" monster will be the lowest id in
        #        the case of a cyclical transform.
        seen = set()
        curr = monster_id
        while curr not in seen:
            seen.add(curr)
            next_ids = self.get_prev_transform_ids_by_monster_id(curr, server)
            if next_ids:
                curr = next_ids.pop()
            else:
                break
        else:
            curr = min(seen)
        return curr

    def get_transform_base_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self.get_monster(self.get_transform_base_id_by_id(monster_id, server), server)

    def get_transform_base(self, monster: MonsterModel):
        return self.get_transform_base_by_id(monster.monster_id, monster.server_priority)

    def monster_is_transform_base_by_id(self, monster_id: int, server: Server = DEFAULT_SERVER) -> bool:
        return self.get_transform_base_id_by_id(monster_id, server) == monster_id

    def monster_is_transform_base(self, monster: MonsterModel) -> bool:
        return self.monster_is_transform_base_by_id(monster.monster_id, monster.server_priority)

    def get_numerical_sort_top_id_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        alt_cards = self.get_alt_ids_by_id(monster_id, server)
        if alt_cards is None:
            return None
        return sorted(alt_cards)[-1]

    def get_numerical_sort_top_monster_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self.get_monster(self.get_numerical_sort_top_id_by_id(monster_id, server), server)

    def get_numerical_sort_top_monster(self, monster: MonsterModel):
        return self.get_numerical_sort_top_monster_by_id(monster.monster_id, monster.server_priority)

    def get_evo_by_monster_id(self, monster_id, server: Server = DEFAULT_SERVER) -> Optional[EvolutionModel]:
        return self._get_edge_model(monster_id, 'back_evolution', server)

    def get_evo_by_monster(self, monster) -> Optional[EvolutionModel]:
        return self._get_edge_model(monster.monster_id, 'back_evolution', monster.server_priority)

    def monster_is_reversible_evo(self, monster: MonsterModel) -> bool:
        prev_evo = self.get_evo_by_monster(monster)
        return prev_evo is not None and prev_evo.reversible

    def monster_is_reincarnated(self, monster: MonsterModel) -> bool:
        if self.monster_is_reversible_evo(monster):
            return False
        while (monster := self.get_prev_evolution_by_monster(monster)):
            if self.monster_is_reversible_evo(monster):
                return True
        return False

    def monster_is_normal_evo(self, monster: MonsterModel) -> bool:
        return not (self.monster_is_reversible_evo(monster)
                    or self.monster_is_reincarnated(monster)
                    or self.monster_is_base(monster))

    def monster_is_first_evo(self, monster: MonsterModel) -> bool:
        prev = self.get_prev_evolution_by_monster(monster)
        if prev:
            return self.get_prev_evolution_by_monster(prev) is None
        return False

    def monster_is_second_ultimate(self, monster: MonsterModel) -> bool:
        if self.monster_is_reversible_evo(monster):
            prev = self.get_prev_evolution_by_monster(monster)
            if prev is not None:
                return self.monster_is_reversible_evo(prev)
        return False

    def true_evo_type_by_monster(self, monster: MonsterModel) -> InternalEvoType:
        if monster.is_equip:
            return InternalEvoType.Assist

        if self.monster_is_base(monster):
            return InternalEvoType.Base

        evo = self.get_evo_by_monster(monster)
        if evo is None:
            # this is possible without being the above case for transforms
            return InternalEvoType.Base
        if evo.is_super_reincarnated:
            return InternalEvoType.SuperReincarnated
        elif evo.is_pixel:
            return InternalEvoType.Pixel

        if self.monster_is_reincarnated(monster):
            return InternalEvoType.Reincarnated
        elif self.monster_is_reversible_evo(monster):
            return InternalEvoType.Ultimate

        return InternalEvoType.Normal

    def true_evo_type_by_monster_id(self, monster_id, server: Server = DEFAULT_SERVER) -> InternalEvoType:
        return self.true_evo_type_by_monster(self.get_monster(monster_id, server))

    def get_prev_evolution_id_by_monster_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self._get_edge_or_none(monster_id, 'back_evolution', server)

    def get_prev_evolution_id_by_monster(self, monster: MonsterModel):
        return self.get_prev_evolution_id_by_monster_id(monster.monster_id, monster.server_priority)

    def get_prev_evolution_by_monster(self, monster: MonsterModel):
        pe = self.get_prev_evolution_id_by_monster(monster)
        return pe and self.get_monster(pe, monster.server_priority)

    def get_next_evolution_ids_by_monster_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self._get_edges(monster_id, 'evolution', server)

    def get_next_evolution_ids_by_monster(self, monster: MonsterModel):
        return self.get_next_evolution_ids_by_monster_id(monster.monster_id, monster.server_priority)

    def get_next_evolutions_by_monster(self, monster: MonsterModel):
        return {self.get_monster(mid, monster.server_priority)
                for mid in self.get_next_evolution_ids_by_monster(monster)}

    def get_prev_transform_ids_by_monster_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self._get_edges(monster_id, 'back_transformation', server)

    def get_prev_transform_ids_by_monster(self, monster: MonsterModel):
        return self.get_prev_transform_ids_by_monster_id(monster.monster_id, monster.server_priority)

    def get_prev_transforms_by_monster(self, monster: MonsterModel):
        return {self.get_monster(mid, monster.server_priority)
                for mid in self.get_prev_transform_ids_by_monster(monster)}

    def get_next_transform_id_by_monster_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self._get_edge_or_none(monster_id, 'transformation', server)

    def get_next_transform_id_by_monster(self, monster: MonsterModel):
        return self.get_next_transform_id_by_monster_id(monster.monster_id, monster.server_priority)

    def get_next_transform_by_monster(self, monster: MonsterModel):
        nt = self.get_next_transform_id_by_monster(monster)
        return nt and self.get_monster(nt, monster.server_priority)

    def evo_mats_by_monster_id(self, monster_id: int, server: Server = DEFAULT_SERVER) -> List[MonsterModel]:
        evo = self.get_evo_by_monster_id(monster_id, server)
        if evo is None:
            return []
        return [self.get_monster(mat, server) for mat in evo.mats]

    def evo_mats_by_monster(self, monster: MonsterModel) -> List[MonsterModel]:
        return self.evo_mats_by_monster_id(monster.monster_id, monster.server_priority)

    def monster_is_farmable_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self.get_monster(monster_id, server).is_farmable

    def monster_is_farmable(self, monster: MonsterModel):
        return self.monster_is_farmable_by_id(monster.monster_id, monster.server_priority)

    def monster_is_farmable_evo_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return any(m
                   for m in self.get_alt_ids_by_id(monster_id, server)
                   if self.monster_is_farmable_by_id(m, server))

    def monster_is_farmable_evo(self, monster: MonsterModel):
        return self.monster_is_farmable_evo_by_id(monster.monster_id, monster.server_priority)

    def monster_is_mp_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self.get_monster(monster_id, server).in_mpshop

    def monster_is_mp(self, monster: MonsterModel):
        return self.monster_is_mp_by_id(monster.monster_id, monster.server_priority)

    def monster_is_mp_evo_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return any(
            m for m in self.get_alt_ids_by_id(monster_id, server) if self.monster_is_mp_by_id(m, server))

    def monster_is_mp_evo(self, monster: MonsterModel):
        return self.monster_is_mp_evo_by_id(monster.monster_id, monster.server_priority)

    def monster_is_pem_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self.get_monster(monster_id, server).in_pem

    def monster_is_pem(self, monster: MonsterModel):
        return self.monster_is_pem_by_id(monster.monster_id, monster.server_priority)

    def monster_is_pem_evo_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return any(m
                   for m in self.get_alt_ids_by_id(monster_id, server)
                   if self.monster_is_pem_by_id(m, server))

    def monster_is_pem_evo(self, monster: MonsterModel):
        return self.monster_is_pem_evo_by_id(monster.monster_id, monster.server_priority)

    def monster_is_rem_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self.get_monster(monster_id, server).in_rem

    def monster_is_rem(self, monster: MonsterModel):
        return self.monster_is_rem_by_id(monster.monster_id, monster.server_priority)

    def monster_is_rem_evo_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return any(m
                   for m in self.get_alt_ids_by_id(monster_id, server)
                   if self.monster_is_rem_by_id(m, server))

    def monster_is_rem_evo(self, monster: MonsterModel):
        return self.monster_is_rem_evo_by_id(monster.monster_id, monster.server_priority)

    def monster_is_exchange_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return bool(self._get_edges(monster_id, 'exchange_from', server))

    def monster_is_exchange(self, monster: MonsterModel):
        return self.monster_is_exchange_by_id(monster.monster_id, monster.server_priority)

    def monster_is_exchange_evo_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return any(m
                   for m in self.get_alt_ids_by_id(monster_id, server)
                   if self.monster_is_exchange_by_id(m, server))

    def monster_is_exchange_evo(self, monster: MonsterModel):
        return self.monster_is_exchange_evo_by_id(monster.monster_id, monster.server_priority)

    def get_monster_exchange_mat_ids_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return self._get_edges(monster_id, 'exchange_from', server)

    def get_monster_exchange_mat_ids(self, monster: MonsterModel):
        return self.get_monster_exchange_mat_ids_by_id(monster.monster_id, monster.server_priority)

    def get_monster_exchange_mats_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        return {self.get_monster(mid, server)
                for mid in self.get_monster_exchange_mat_ids_by_id(monster_id, server)}

    def get_monster_exchange_mats(self, monster: MonsterModel):
        return self.get_monster_exchange_mats_by_id(monster.monster_id, monster.server_priority)

    def monster_is_vendor_exchange_by_id(self, monster_id, server: Server = DEFAULT_SERVER):
        ids = self.get_monster_exchange_mats_by_id(monster_id, server)
        return bool(ids) and all(15 in [t.value for t in m.types] for m in ids)

    def monster_is_vendor_exchange(self, monster: MonsterModel):
        return self.monster_is_vendor_exchange_by_id(monster.monster_id, monster.server_priority)

    def monster_is_new(self, monster: MonsterModel):
        latest_time = max(am.reg_date for am in self.get_alt_monsters(monster))
        return monster.reg_date == latest_time

    def monster_acquisition(self, monster: MonsterModel):
        if self.monster_is_rem_evo(monster):
            return 'REM Card'
        elif self.monster_is_mp_evo(monster):
            return 'MP Shop Card'
        elif self.monster_is_farmable_evo(monster):
            return 'Farmable Card'
        elif self.monster_is_pem_evo(monster):
            return 'PEM Card'

    def numeric_next_monster_id_by_id(self, monster_id: int, server: Server = DEFAULT_SERVER) -> Optional[int]:
        next_monster = None
        offset = 1
        while next_monster is None and monster_id + offset <= self.max_monster_id:
            next_monster = self.get_monster(monster_id + offset, server)
            offset += 1
        if next_monster is None:
            return None
        return next_monster.monster_id

    def numeric_next_monster(self, monster: MonsterModel) -> Optional[MonsterModel]:
        next_monster_id = self.numeric_next_monster_id_by_id(monster.monster_id, monster.server_priority)
        if next_monster_id is None:
            return None
        return self.get_monster(next_monster_id, monster.server_priority)

    def numeric_prev_monster_id_by_id(self, monster_id, server: Server = DEFAULT_SERVER) -> Optional[int]:
        prev_monster = None
        offset = 1
        while prev_monster is None and monster_id - offset >= 1:
            prev_monster = self.get_monster(monster_id - offset, server)
            offset += 1
        if prev_monster is None:
            return None
        return prev_monster.monster_id

    def numeric_prev_monster(self, monster: MonsterModel) -> Optional[MonsterModel]:
        prev_monster_id = self.numeric_prev_monster_id_by_id(monster.monster_id, monster.server_priority)
        if prev_monster_id is None:
            return None
        return self.get_monster(prev_monster_id, monster.server_priority)

    def evo_gem_monster_by_id(self, monster_id, server: Server = DEFAULT_SERVER) -> Optional[MonsterModel]:
        this_monster = self.get_monster(monster_id, server)
        if this_monster.evo_gem_id is None:
            return None
        return self.get_monster(this_monster.evo_gem_id, server)

    def evo_gem_monster(self, monster: MonsterModel) -> Optional[MonsterModel]:
        return self.evo_gem_monster_by_id(monster.monster_id, monster.server_priority)

    def get_monster_from_evo_gem(self, monster: MonsterModel) -> Optional[MonsterModel]:
        return self.get_monster(self._get_edge_or_none(monster.monster_id, "evo_gem_of", monster.server_priority), 
                                monster.server_priority)

    def monster_is_evo_gem(self, monster: MonsterModel) -> bool:
        return bool(self.get_monster_from_evo_gem(monster))

    def material_of_ids_by_id(self, monster_id: int, server: Server = DEFAULT_SERVER) -> List[int]:
        return sorted(self._get_edges(monster_id, 'material_of', server))

    def material_of_ids(self, monster: MonsterModel) -> List[int]:
        return self.material_of_ids_by_id(monster.monster_id, monster.server_priority)

    def material_of_monsters(self, monster: MonsterModel) -> List[MonsterModel]:
        return [self.get_monster(m, monster.server_priority)
                for m in self.material_of_ids(monster)]

    def monster_difference(self, monster: MonsterModel, server: Server = DEFAULT_SERVER) -> MonsterDifference:
        return monster.get_difference(self.get_monster(monster.monster_id, server))
