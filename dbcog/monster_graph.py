import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, cast

from networkx import MultiDiGraph
from tsutils.enums import Server

from .database_manager import DBCogDatabase
from .models.active_skill_model import ActiveSkillModel
from .models.awakening_model import AwakeningModel
from .models.awoken_skill_model import AwokenSkillModel
from .models.base_model import BaseModel
from .models.enum_types import DEFAULT_SERVER, InternalEvoType, SERVERS
from .models.evolution_model import EvolutionModel
from .models.exchange_model import ExchangeModel
from .models.leader_skill_model import LeaderSkillModel
from .models.monster.monster_difference import MonsterDifference
from .models.monster_model import MonsterModel
from .models.series_model import SeriesModel

logger = logging.getLogger('red.padbot-cogs.dbcog')

M = TypeVar('M', bound=BaseModel)

MONSTER_QUERY = """SELECT
  monsters{0}.*,
  monster_name_overrides.name_en AS name_override,
  monster_name_overrides.is_translation,
  leader_skills{0}.name_ja AS ls_name_ja,
  leader_skills{0}.name_en AS ls_name_en,
  leader_skills{0}.name_ko AS ls_name_ko,
  leader_skills{0}.desc_ja AS ls_desc_ja,
  leader_skills{0}.desc_en AS ls_desc_en,
  leader_skills{0}.desc_ko AS ls_desc_ko,
  leader_skills{0}.max_hp,
  leader_skills{0}.max_atk,
  leader_skills{0}.max_rcv,
  leader_skills{0}.max_shield,
  leader_skills{0}.max_combos,
  leader_skills{0}.bonus_damage,
  leader_skills{0}.mult_bonus_damage,
  leader_skills{0}.extra_time,
  leader_skills{0}.tags,
  COALESCE(series.series_id, 0) AS s_series_id,
  exchanges.target_monster_id AS evo_gem_id,
  drops.drop_id,
  sizes.mp4_size,
  sizes.gif_size,
  sizes.hq_png_size,
  sizes.hq_gif_size
FROM
  monsters{0}
  LEFT OUTER JOIN leader_skills{0} ON monsters{0}.leader_skill_id = leader_skills{0}.leader_skill_id
  LEFT OUTER JOIN active_skills{0} ON monsters{0}.active_skill_id = active_skills{0}.active_skill_id
  LEFT OUTER JOIN monster_series ON monsters{0}.monster_id = monster_series.monster_id AND priority = 1
  LEFT OUTER JOIN series ON monster_series.series_id = series.series_id
  LEFT OUTER JOIN monsters{0} AS target_monsters ON monsters{0}.name_ja || 'の希石' = target_monsters.name_ja
  LEFT OUTER JOIN exchanges ON target_monsters.monster_id = exchanges.target_monster_id
  LEFT OUTER JOIN drops ON monsters{0}.monster_id = drops.monster_id
  LEFT OUTER JOIN monster_name_overrides ON monsters{0}.monster_id = monster_name_overrides.monster_id
  LEFT OUTER JOIN monster_image_sizes AS sizes ON monsters{0}.monster_id = sizes.monster_id
GROUP BY
  monsters{0}.monster_id"""

ACTIVE_QUERY = """SELECT
  act.active_skill_id,
  act.compound_skill_type_id,
  act.name_ja AS act_name_ja,
  act.name_en AS act_name_en,
  act.name_ko AS act_name_ko,
  act.desc_ja AS act_desc_ja,
  act.desc_en AS act_desc_en,
  act.desc_ko AS act_desc_ko,
  act.desc_templated_ja AS act_desc_templated_ja,
  act.desc_templated_en AS act_desc_templated_en,
  act.desc_templated_ko AS act_desc_templated_ko,
  act.desc_official_ja AS act_desc_official_ja,
  act.desc_official_ko AS act_desc_official_ko,
  act.desc_official_en AS act_desc_official_en,
  act.cooldown_turns_max,
  act.cooldown_turns_min,
  ass.active_subskill_id,
  ass.name_ja AS ass_name_ja,
  ass.name_en AS ass_name_en,
  ass.name_ko AS ass_name_ko,
  ass.desc_ja AS ass_desc_ja,
  ass.desc_en AS ass_desc_en,
  ass.desc_ko AS ass_desc_ko,
  ass.desc_templated_ja AS ass_desc_templated_ja,
  ass.desc_templated_en AS ass_desc_templated_en,
  ass.desc_templated_ko AS ass_desc_templated_ko,
  ass.board_65 AS ass_board_65,
  ass.board_76 AS ass_board_76,
  ass.cooldown AS ass_cooldown,
  ap.active_part_id,
  ap.active_skill_type_id,
  ap.desc_ja AS ap_desc_ja,
  ap.desc_en AS ap_desc_en,
  ap.desc_ko AS ap_desc_ko,
  ap.desc_templated_ja AS ap_desc_templated_ja,
  ap.desc_templated_en AS ap_desc_templated_en,
  ap.desc_templated_ko AS ap_desc_templated_ko,
  act_ass.order_idx AS subskill_idx
FROM
  active_skills{0} AS act
  JOIN active_skills_subskills{0} AS act_ass ON act.active_skill_id = act_ass.active_skill_id
  JOIN active_subskills{0} AS ass ON act_ass.active_subskill_id = ass.active_subskill_id
  JOIN active_subskills_parts{0} AS ass_ap ON ass.active_subskill_id = ass_ap.active_subskill_id
  JOIN active_parts{0} AS ap ON ass_ap.active_part_id = ap.active_part_id
ORDER BY
  ass_ap.order_idx,
  act_ass.order_idx
"""

EVOS_QUERY = """SELECT
  evolutions{0}.*
FROM
  evolutions{0}"""

TRANSFORMS_QUERY = """SELECT
  transformations{0}.*
FROM
  transformations{0}"""

AWAKENINGS_QUERY = """SELECT
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
WHERE
  start_timestamp < strftime('%s', 'now')
"""

EXCHANGE_QUERY = """SELECT
  *
FROM
  exchanges
WHERE
  start_timestamp < strftime('%s', 'now')
"""

SIMPLE_QUERY = """SELECT
  *
FROM
  {0}
"""

SERVER_ID_WHERE_CONDITION = " AND server_id = {}"


class MonsterGraph:
    def __init__(self, database: DBCogDatabase, debug_monster_ids: Optional[List[int]] = None):
        self.issues = []
        self.debug_monster_ids = debug_monster_ids

        self.database = database
        self.max_monster_id = -1
        self.graph_dict: Dict[Server, MultiDiGraph] = {
            Server.COMBINED: self.build_graph(Server.COMBINED),
            Server.NA: self.build_graph(Server.NA),
        }

        self._cache_graphs()

    def build_graph(self, server: Server) -> MultiDiGraph:
        graph = MultiDiGraph()

        table_suffix = ""
        where = ""
        if server != Server.COMBINED:
            table_suffix = "_" + server.value.lower()
            where = SERVER_ID_WHERE_CONDITION.format(["JP", "NA", "KR"].index(server.value))

        ms = self.database.query_many(MONSTER_QUERY.format(table_suffix))
        es = self.database.query_many(EVOS_QUERY.format(table_suffix))
        tfs = self.database.query_many(TRANSFORMS_QUERY.format(table_suffix))
        aws = self.database.query_many(AWAKENINGS_QUERY.format(table_suffix))
        ems = self.database.query_many(EGG_QUERY.format(table_suffix) + where)
        exs = self.database.query_many(EXCHANGE_QUERY.format(table_suffix) + where)

        as_query = self.database.query_many(ACTIVE_QUERY.format(table_suffix))
        acts = {}
        for row in as_query:
            if row.active_skill_id not in acts:
                acts[row.active_skill_id] = {
                    'active_skill_id': row.active_skill_id,
                    'compound_skill_type_id': row.compound_skill_type_id,
                    'name_ja': row.act_name_ja,
                    'name_en': row.act_name_en,
                    'name_ko': row.act_name_ko,
                    'desc_ja': row.act_desc_ja,
                    'desc_en': row.act_desc_en,
                    'desc_ko': row.act_desc_ko,
                    'desc_templated_ja': row.act_desc_templated_ja,
                    'desc_templated_en': row.act_desc_templated_en,
                    'desc_templated_ko': row.act_desc_templated_ko,
                    'desc_official_ja': row.act_desc_official_ja,
                    'desc_official_ko': row.act_desc_official_ko,
                    'desc_official_en': row.act_desc_official_en,
                    'cooldown_turns_max': row.cooldown_turns_max,
                    'cooldown_turns_min': row.cooldown_turns_min,

                    'active_subskills': []
                }
            skill = acts[row.active_skill_id]
            if len(skill['active_subskills']) <= row.subskill_idx:
                skill['active_subskills'].append({
                    'active_subskill_id': row.active_subskill_id,
                    'name_ja': row.ass_name_ja,
                    'name_en': row.ass_name_en,
                    'name_ko': row.ass_name_ko,
                    'desc_ja': row.ass_desc_ja,
                    'desc_en': row.ass_desc_en,
                    'desc_ko': row.ass_desc_ko,
                    'desc_templated_ja': row.ass_desc_templated_ja,
                    'desc_templated_en': row.ass_desc_templated_en,
                    'desc_templated_ko': row.ass_desc_templated_ko,
                    'board_65': row.ass_board_65,
                    'board_76': row.ass_board_76,
                    'cooldown': row.ass_cooldown,

                    'active_parts': []
                })
            subskill = skill['active_subskills'][row.subskill_idx]
            subskill['active_parts'].append({
                'active_part_id': row.active_part_id,
                'active_skill_type_id': row.active_skill_type_id,
                'desc_ja': row.ap_desc_ja,
                'desc_en': row.ap_desc_en,
                'desc_ko': row.ap_desc_ko,
                'desc_templated_ja': row.ap_desc_templated_ja,
                'desc_templated_en': row.ap_desc_templated_en,
                'desc_templated_ko': row.ap_desc_templated_ko,
            })
        acts = {asid: ActiveSkillModel(**act) for asid, act in acts.items()}

        mtoawo = defaultdict(list)
        for a in aws:
            awoken_skill_model = AwokenSkillModel(**a)
            awakening_model = AwakeningModel(awoken_skill_model=awoken_skill_model, **a)
            mtoawo[a.monster_id].append(awakening_model)

        mtoegg = defaultdict(lambda: {'pem': False, 'rem': False, 'adpem': False})
        for e in ems:
            data = json.loads(e.contents)
            e_type = 'pem' if e.type == "PEM" else 'adpem' if e.type == "VEM" else 'rem'
            for m in data:
                idx = int(m[1:-1])  # Remove parentheses
                mtoegg[idx][e_type] = True

        ss_query = self.database.query_many(SIMPLE_QUERY.format('series'))
        series = {}
        for row in ss_query:
            series[row.series_id] = SeriesModel(series_id=row.series_id,
                                                name_ja=row.name_ja,
                                                name_en=row.name_en,
                                                name_ko=row.name_ko,
                                                series_type=row.series_type
                                                )

        mss_query = self.database.query_many(SIMPLE_QUERY.format('monster_series'))
        monster_series = defaultdict(set)
        for row in mss_query:
            monster_series[row.monster_id].add(series[row.series_id])

        for m in ms:
            if self.debug_monster_ids is not None and m.monster_id not in self.debug_monster_ids:
                continue
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
                                        tags=m.tags,
                                        ) if m.leader_skill_id != 0 else None

            m_model = MonsterModel(monster_id=m.monster_id,
                                   base_evo_id=m.base_id,
                                   monster_no_jp=m.monster_no_jp,
                                   monster_no_na=m.monster_no_na,
                                   monster_no_kr=m.monster_no_kr,
                                   name_is_translation=m.is_translation,
                                   awakenings=mtoawo[m.monster_id],
                                   leader_skill=ls_model,
                                   active_skill=acts.get(m.active_skill_id),
                                   series=series[m.s_series_id],
                                   all_series=monster_series[m.monster_id] or {series[0]},
                                   series_id=m.s_series_id,
                                   group_id=m.group_id,
                                   collab_id=m.collab_id,
                                   attribute_1_id=m.attribute_1_id,
                                   attribute_2_id=m.attribute_2_id,
                                   name_ja=m.name_ja,
                                   name_en=m.name_en,
                                   name_ko=m.name_ko,
                                   name_en_override=m.name_override,
                                   rarity=m.rarity,
                                   is_farmable=m.drop_id is not None,
                                   in_pem=mtoegg[m.monster_id]['pem'],
                                   in_rem=mtoegg[m.monster_id]['rem'],
                                   in_vem=mtoegg[m.monster_id]['adpem'],
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
                                   bgm_id=m.bgm_id,
                                   cost=m.cost,
                                   level=m.level,
                                   exp=m.exp,
                                   fodder_exp=m.fodder_exp,
                                   limit_mult=m.limit_mult,
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
                                   drop_id=m.drop_id,
                                   mp4_size=m.mp4_size,
                                   gif_size=m.gif_size,
                                   hq_png_size=m.hq_png_size,
                                   hq_gif_size=m.hq_gif_size
                                   )
            if not m_model:
                continue

            graph.add_node(m.monster_id, model=m_model)
            self.max_monster_id = max(self.max_monster_id, m.monster_id)

            if m.evo_gem_id:
                if self.debug_monster_ids is None or m.evo_gem_id in self.debug_monster_ids:
                    graph.add_edge(m.monster_id, m.evo_gem_id, type='evo_gem_from')
                    graph.add_edge(m.evo_gem_id, m.monster_id, type='evo_gem_of')

        for e in es:
            if self.debug_monster_ids is not None:
                if e.from_id not in self.debug_monster_ids or e.to_id not in self.debug_monster_ids:
                    continue

            evo_model = EvolutionModel(
                evolution_type=e.evolution_type,
                reversible=e.reversible,
                from_id=e.from_id,
                to_id=e.to_id,
                mat_1_id=self.debug_validate_id(e.mat_1_id),
                mat_2_id=self.debug_validate_id(e.mat_2_id),
                mat_3_id=self.debug_validate_id(e.mat_3_id),
                mat_4_id=self.debug_validate_id(e.mat_4_id),
                mat_5_id=self.debug_validate_id(e.mat_5_id),
                tstamp=e.tstamp,
            )

            graph.add_edge(evo_model.from_id, evo_model.to_id, type='evolution', model=evo_model)
            graph.add_edge(evo_model.to_id, evo_model.from_id, type='back_evolution', model=evo_model)

            # for material_of queries
            already_used_in_this_evo = set()  # don't add same mat more than once per evo
            for mat in evo_model.mats:
                if mat in already_used_in_this_evo:
                    continue
                graph.add_edge(
                    mat, evo_model.to_id, type="material_of", model=evo_model)
                already_used_in_this_evo.add(mat)

        for tf in tfs:
            if self.debug_monster_ids is not None:
                if tf.from_monster_id not in self.debug_monster_ids or tf.to_monster_id not in self.debug_monster_ids:
                    continue

            # Make a model with percentages here.

            graph.add_edge(tf.from_monster_id, tf.to_monster_id, type='transformation')
            graph.add_edge(tf.to_monster_id, tf.from_monster_id, type='back_transformation')

        exchanges = defaultdict(set)
        for ex in exs:
            model = ExchangeModel(**ex)
            for vendor_id in re.findall(r'\d+', ex.required_monster_ids):
                if self.debug_monster_ids is not None:
                    if ex.target_monster_id not in self.debug_monster_ids \
                            or int(vendor_id) not in self.debug_monster_ids:
                        continue
                exchanges[(int(vendor_id), ex.target_monster_id)].add(model)
        for (sell_id, buy_id), models in exchanges.items():
            graph.add_edge(buy_id, sell_id, type='exchange_from', models=models)
            graph.add_edge(sell_id, buy_id, type='exchange_for', models=models)

        return graph

    def _cache_graphs(self) -> None:
        for server in self.graph_dict:
            for mid in self.graph_dict[server].nodes:
                if 'model' in self.graph_dict[server].nodes[mid]:
                    alt_ids = self.process_alt_ids(self.get_monster(mid, server=server))
                    self.graph_dict[server].nodes[mid]['alt_versions'] = alt_ids
                    if self.debug_monster_ids is not None:
                        self.graph_dict[server].nodes[mid]['model'].base_evo_id = alt_ids[0]
                else:
                    alert = False
                    for edges in self.graph_dict[server][mid].values():
                        for edge in edges.values():
                            if not edge['type'].startswith('exchange'):
                                alert |= True
                    if alert:
                        self.issues.append(f"{mid} has no model in the {server.name} graph.")

    def _get_edges(self, monster: MonsterModel, etype) -> Set[int]:
        return {mid for mid, atlas in self.graph_dict[monster.server_priority][monster.monster_id].items()
                for edge in atlas.values() if edge.get('type') == etype}

    def _get_edge_or_none(self, monster: MonsterModel, etype: str) -> Optional[int]:
        edges = self._get_edges(monster, etype)
        if edges:
            return edges.pop()

    def _get_edge_model_set(self, monster: MonsterModel, etype: str) -> Set[BaseModel]:
        possible_results = set()
        for atlas in self.graph_dict[monster.server_priority][monster.monster_id].values():
            for edge in atlas.values():
                if edge.get('type') == etype:
                    possible_results.update(edge['models'])
        return possible_results

    def _get_newest_edge_model(self, monster: MonsterModel, etype: str) -> Optional[BaseModel]:
        possible_results = set()
        for atlas in self.graph_dict[monster.server_priority][monster.monster_id].values():
            for edge in atlas.values():
                if edge.get('type') == etype:
                    possible_results.add(edge['model'])
        if possible_results:
            return min(possible_results, key=lambda x: x.tstamp)

    def get_monster(self, monster_id: int, *, server: Server = DEFAULT_SERVER, do_logging: bool = False) \
            -> Optional[MonsterModel]:
        if monster_id not in self.graph_dict[server].nodes:
            return None
        if 'model' not in self.graph_dict[server].nodes[monster_id]:
            return None
        return self.graph_dict[server].nodes[monster_id]['model']

    def get_all_monsters(self, server: Server) -> Set[MonsterModel]:
        # Fail gracefully if one of the nodes doesn't exist
        # TODO: log which node doesn't exist? Or unneeded bc we will do that at startup
        return {mdata['model'] for mdata in self.graph_dict[server].nodes.values() if mdata.get('model')}

    def get_evo_tree(self, monster: MonsterModel) -> List[MonsterModel]:
        while (prev := self.get_prev_evolution(monster)):
            monster = prev
        return self.get_evo_tree_from_base(monster)

    def get_evo_tree_from_base(self, base_monster: MonsterModel) -> List[MonsterModel]:
        mons = [base_monster]
        for evo in sorted(self.get_next_evolutions(base_monster), key=lambda m: m.monster_id):
            mons += self.get_evo_tree_from_base(evo)
        return mons

    def get_transform_monsters(self, monster: MonsterModel) -> Set[MonsterModel]:
        mons = set()
        to_check = {monster}
        while to_check:
            mon = to_check.pop()
            if mon in mons:
                continue
            to_check.update(self.get_next_transforms(mon))
            to_check.update(self.get_prev_transforms(mon))
            mons.add(mon)
        return mons

    def process_alt_ids(self, monster: MonsterModel) -> List[int]:
        return [m.monster_id for m in self.process_alt_monsters_from_base(self.get_base_monster(monster))]

    def process_alt_monsters_from_base(self, base_monster: MonsterModel) -> List[MonsterModel]:
        ids = [base_monster]
        for transform in sorted(self.get_next_transforms(base_monster), key=self.get_id_order_key):
            if transform and (transform.monster_id > base_monster.monster_id
                              or transform.monster_id == 5802):  # I hate DMG very much
                ids += [mid for mid in self.process_alt_monsters_from_base(transform) if mid not in ids]
        for evo in sorted(self.get_next_evolutions(base_monster), key=self.get_id_order_key):
            ids += self.process_alt_monsters_from_base(evo)
        return ids

    def get_id_order_key(self, monster: MonsterModel) -> Tuple[Any, ...]:
        evo_ordering = {
            InternalEvoType.Reincarnated: -1,
            InternalEvoType.SuperReincarnated: -1,
            InternalEvoType.Base: 0,
            InternalEvoType.Normal: 0,
            InternalEvoType.Ultimate: 1,
            InternalEvoType.Pixel: 2,
            InternalEvoType.Assist: 3,
        }
        return (
            evo_ordering[self.true_evo_type(monster)],
            '覚醒' in monster.name_ja or 'awoken' in monster.name_en.lower(),
            monster.monster_id,
        )

    def get_alt_ids(self, monster: MonsterModel) -> List[int]:
        return self.graph_dict[monster.server_priority].nodes[monster.monster_id]['alt_versions']

    def get_alt_monsters(self, monster: MonsterModel) -> List[MonsterModel]:
        return [self.get_monster(m_id, server=monster.server_priority) for m_id in self.get_alt_ids(monster)]

    def get_monsters_with_same_id(self, monster: MonsterModel) -> Set[MonsterModel]:
        return {*filter(None, [self.get_monster(monster.monster_id % 10_000, server=monster.server_priority),
                               self.get_monster(monster.monster_id + 10_000, server=monster.server_priority)])}

    def get_base_id(self, monster) -> int:
        # This fixes DMG.  I *hate* DMG.
        if monster.base_evo_id == 5802:
            return 5810

        while True:
            prev = self.get_prev_transform(monster)
            if prev is None:
                break
            if prev.monster_id >= monster.monster_id:
                break
            monster = prev

        if self.debug_monster_ids is not None:
            while (prev := self.get_prev_evolution(monster)):
                monster = prev
            return monster.monster_id
        else:
            return monster.base_evo_id

    def get_base_monster(self, monster: MonsterModel) -> MonsterModel:
        return self.get_monster(self.get_base_id(monster), server=monster.server_priority)

    def monster_is_base(self, monster: MonsterModel) -> bool:
        return self.get_base_id(monster) == monster.monster_id

    def get_transform_base(self, monster: MonsterModel) -> MonsterModel:
        # NOTE: This assumes that no two monsters will transform to the same monster. This
        #        also doesn't work for monsters like DMG which are transforms but also base
        #        cards.  This also assumes that the "base" monster will be the lowest id in
        #        the case of a cyclical transform.
        seen = set()
        curr = monster
        while curr not in seen:
            seen.add(curr)
            prev_mon = self.get_prev_transform(curr)
            if prev_mon is not None:
                curr = prev_mon
            else:
                break
        else:
            curr = min(seen, key=lambda m: m.monster_id)
        return curr

    def monster_is_transform_base(self, monster: MonsterModel) -> bool:
        return self.get_transform_base(monster) == monster

    def get_numerical_sort_top_monster(self, monster: MonsterModel) -> Optional[MonsterModel]:
        alt_cards = self.get_alt_monsters(monster)
        if alt_cards is None:
            return None
        return sorted(alt_cards, key=lambda m: m.monster_id)[-1]

    def get_evolution(self, monster) -> Optional[EvolutionModel]:
        return self._get_newest_edge_model(monster, 'back_evolution')

    def monster_is_reversible_evo(self, monster: MonsterModel) -> bool:
        prev_evo = self.get_evolution(monster)
        return prev_evo is not None and prev_evo.reversible

    def monster_is_reincarnated(self, monster: MonsterModel) -> bool:
        if self.monster_is_reversible_evo(monster):
            return False
        while (monster := self.get_prev_evolution(monster)):
            if self.monster_is_reversible_evo(monster):
                return True
        return False

    def monster_is_normal_evo(self, monster: MonsterModel) -> bool:
        return not (self.monster_is_reversible_evo(monster)
                    or self.monster_is_reincarnated(monster)
                    or self.monster_is_base(monster))

    def monster_is_first_evo(self, monster: MonsterModel) -> bool:
        prev = self.get_prev_evolution(monster)
        if prev:
            return self.get_prev_evolution(prev) is None
        return False

    def monster_is_second_ultimate(self, monster: MonsterModel) -> bool:
        if self.monster_is_reversible_evo(monster):
            prev = self.get_prev_evolution(monster)
            if prev is not None:
                return self.monster_is_reversible_evo(prev)
        return False

    def true_evo_type(self, monster: MonsterModel) -> InternalEvoType:
        if monster.is_equip:
            return InternalEvoType.Assist
        if self.monster_is_base(monster):
            return InternalEvoType.Base

        evo = self.get_evolution(monster)
        if evo is None:
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

    def get_prev_evolution(self, monster: MonsterModel) -> Optional[MonsterModel]:
        pe = self._get_edge_or_none(monster, 'back_evolution')
        return pe and self.get_monster(pe, server=monster.server_priority)

    def get_next_evolutions(self, monster: MonsterModel) -> Set[MonsterModel]:
        return {self.get_monster(mid, server=monster.server_priority)
                for mid in self._get_edges(monster, 'evolution')}

    def get_prev_transforms(self, monster: MonsterModel) -> Set[MonsterModel]:
        return {self.get_monster(mid, server=monster.server_priority)
                for mid in self._get_edges(monster, 'back_transformation')}

    def get_prev_transform(self, monster: MonsterModel) -> Optional[MonsterModel]:
        # This doesn't need a special function, so I'll remove it later
        transforms = self.get_prev_transforms(monster)
        if not transforms:
            return None
        return min(transforms, key=lambda m: m.monster_id)

    def get_next_transforms(self, monster: MonsterModel) -> Set[MonsterModel]:
        return {self.get_monster(mid, server=monster.server_priority)
                for mid in self._get_edges(monster, 'transformation')}

    def get_next_transform(self, monster: MonsterModel) -> Optional[MonsterModel]:
        # Figure out how to get rid of this
        transforms = self.get_next_transforms(monster)
        if not transforms:
            return None
        return max(transforms, key=lambda m: m.monster_id)

    def get_all_prev_evolutions(self, monster: MonsterModel, *, include_self: bool = True) -> List[MonsterModel]:
        ret = []
        if include_self:
            ret.append(monster)
        cur_mon = monster
        while True:
            pe = self.get_prev_evolution(cur_mon)
            if pe is None:
                break
            ret.append(pe)
            cur_mon = pe
        return ret

    def get_all_prev_transforms(self, monster: MonsterModel, *, include_self: bool = True,
                                cyclical_wrap: bool = False) -> List[MonsterModel]:
        ret = []
        if include_self:
            ret.append(monster)
        cur_mon = monster
        is_cycle = False
        while True:
            pt = self.get_prev_transform(cur_mon)
            if pt is None:
                break
            if pt.monster_id == monster.monster_id:
                is_cycle = True
                break
            ret.append(pt)
            cur_mon = pt
        if is_cycle and not cyclical_wrap:
            # remove everything that comes "after" monster in the cycle (i.e. has a higher monster id)
            to_pop = []
            for i, mon in enumerate(ret):
                if mon.monster_id > monster.monster_id:
                    to_pop.append(i)
            to_pop.reverse()
            for i in to_pop:
                ret.pop(i)
        return ret

    def get_all_next_evolutions(self, monster: MonsterModel, include_self: bool = True) -> Set[MonsterModel]:
        to_parse = {monster}
        ret = set()
        while to_parse:
            mon = to_parse.pop()
            if mon in ret:
                continue
            ret.add(mon)
            to_parse.update(self.get_next_evolutions(mon))
        if not include_self:
            ret.remove(monster)
        return ret

    def get_monster_depth(self, monster: MonsterModel) -> float:
        if monster.monster_id == 5802:
            # DMG sucks!
            return 0

        depth = 0.0
        while None is not (prev := self.get_prev_transform(monster)) \
                and prev.monster_id < monster.monster_id:
            monster = prev
            depth += .01
        while None is not (monster := self.get_prev_evolution(monster)):
            depth += 1
        return depth

    def get_adjusted_rarity(self, monster: MonsterModel) -> float:
        # After the revo/srevo changes, rarity doesn't work, and Mega GFEs means that depth doesn't work
        # The max of base rarity + the depth or the current rarity.  This fixes revo rarities being nerfed
        return max(self.get_base_monster(monster).rarity + self.get_monster_depth(monster), monster.rarity)

    def evo_mats(self, monster: MonsterModel) -> List[MonsterModel]:
        evo = self.get_evolution(monster)
        if evo is None:
            return []
        return [self.get_monster(mat, server=monster.server_priority) for mat in evo.mats]

    def monster_is_farmable_evo(self, monster: MonsterModel) -> bool:
        return any(alt.is_farmable for alt in self.get_alt_monsters(monster))

    def monster_is_mp_evo(self, monster: MonsterModel) -> bool:
        return any(alt.in_mpshop for alt in self.get_alt_monsters(monster))

    def monster_is_pem_evo(self, monster: MonsterModel) -> bool:
        return any(alt.in_pem for alt in self.get_alt_monsters(monster))

    def monster_is_rem_evo(self, monster: MonsterModel) -> bool:
        return any(alt.in_rem for alt in self.get_alt_monsters(monster))

    def monster_is_vem_evo(self, monster: MonsterModel) -> bool:
        return any(alt.in_vem for alt in self.get_alt_monsters(monster))

    def monster_is_orb_skin_evo(self, monster: MonsterModel) -> bool:
        return any(alt.orb_skin_id for alt in self.get_alt_monsters(monster))

    def monster_is_bgm_evo(self, monster: MonsterModel) -> bool:
        return any(alt.bgm_id for alt in self.get_alt_monsters(monster))

    def monster_is_exchange(self, monster: MonsterModel) -> bool:
        return bool(self._get_edges(monster, 'exchange_from'))

    def monster_is_exchange_evo(self, monster: MonsterModel) -> bool:
        return any(self.monster_is_exchange(alt) for alt in self.get_alt_monsters(monster))

    def get_monster_exchange_mat_ids(self, monster: MonsterModel) -> Set[int]:
        return self._get_edges(monster, 'exchange_from')

    def get_monster_exchange_models(self, monster: MonsterModel) -> Set[ExchangeModel]:
        return cast(Set[ExchangeModel], self._get_edge_model_set(monster, 'exchange_from'))

    def get_monster_exchange_mats(self, monster: MonsterModel) -> Set[MonsterModel]:
        return {self.get_monster(mid, server=monster.server_priority)
                for mid in self.get_monster_exchange_mat_ids(monster)}

    def monster_is_vendor_exchange(self, monster: MonsterModel) -> bool:
        ids = self.get_monster_exchange_mats(monster)
        return bool(ids) and all(15 in [t.value for t in m.types] for m in ids)

    def monster_is_black_medal_exchange(self, monster: MonsterModel) -> bool:
        return 5155 in [m.monster_id for m in self.get_monster_exchange_mats(monster)]

    def monster_is_black_medal_exchange_evo(self, monster: MonsterModel) -> bool:
        return any(self.monster_is_black_medal_exchange(alt) for alt in self.get_alt_monsters(monster))

    def monster_is_currently_exchangable(self, monster: MonsterModel, server: Optional[Server] = None) -> bool:
        models = self.get_monster_exchange_models(monster)
        now = datetime.now()
        for model in models:
            if model.start_timestamp < now < model.end_timestamp \
                    and (server is None or server == model.server):
                return True
        return False

    def monster_is_currently_exchangable_evo(self, monster: MonsterModel, server: Optional[Server] = None) -> bool:
        return any(self.monster_is_currently_exchangable(alt, server) for alt in self.get_alt_monsters(monster))

    def monster_is_permanent_exchange(self, monster: MonsterModel) -> bool:
        return any(model.permanent or model.end_timestamp.year > 2030
                   for model in self.get_monster_exchange_models(monster))

    def monster_is_permanent_exchange_evo(self, monster: MonsterModel) -> bool:
        return any(self.monster_is_permanent_exchange(alt) for alt in self.get_alt_monsters(monster))

    def monster_is_temporary_exchange(self, monster: MonsterModel) -> bool:
        """Not necessarily a current exchange"""
        return not all(model.permanent and model.end_timestamp.year > 2030
                       for model in self.get_monster_exchange_models(monster))

    def monster_is_temporary_exchange_evo(self, monster: MonsterModel) -> bool:
        """Not necessarily a current exchange"""
        return any(self.monster_is_temporary_exchange(alt) for alt in self.get_alt_monsters(monster))

    def monster_is_new(self, monster: MonsterModel) -> bool:
        latest_time = max(am.reg_date for am in self.get_alt_monsters(monster))
        return monster.reg_date == latest_time

    def monster_acquisition(self, monster: MonsterModel) -> str:
        if self.monster_is_rem_evo(monster):
            return 'REM Card'
        elif self.monster_is_mp_evo(monster):
            return 'MP Shop Card'
        elif self.monster_is_farmable_evo(monster):
            return 'Farmable Card'
        elif self.monster_is_pem_evo(monster):
            return 'PEM Card'
        elif self.monster_is_vem_evo(monster):
            return 'AdPEM Card'

    def numeric_next_monster(self, monster: MonsterModel) -> Optional[MonsterModel]:
        next_monster = None
        offset = 1
        while next_monster is None and monster.monster_id + offset <= self.max_monster_id:
            next_monster = self.get_monster(monster.monster_id + offset, server=monster.server_priority)
            offset += 1
        if next_monster is None:
            return None
        return next_monster

    def numeric_prev_monster(self, monster: MonsterModel) -> Optional[MonsterModel]:
        prev_monster = None
        offset = 1
        while prev_monster is None and monster.monster_id - offset >= 1:
            prev_monster = self.get_monster(monster.monster_id - offset, server=monster.server_priority)
            offset += 1
        if prev_monster is None:
            return None
        return prev_monster

    def evo_gem_monster(self, monster: MonsterModel) -> Optional[MonsterModel]:
        if monster.evo_gem_id is None:
            return None
        return self.get_monster(monster.evo_gem_id, server=monster.server_priority)

    def get_monster_from_evo_gem(self, monster: MonsterModel) -> Optional[MonsterModel]:
        return self.get_monster(self._get_edge_or_none(monster, "evo_gem_of"), server=monster.server_priority)

    def monster_is_evo_gem(self, monster: MonsterModel) -> bool:
        # Evo gems can no longer be calculated via exchange as of Pixel Volcano Dragon
        return monster.name_en.endswith("'s Gem") or monster.name_ja.endswith("の希石")

    def monster_is_gfe_exchange(self, monster: MonsterModel, stars: Optional[int] = None) -> bool:
        monsters = {self.get_monster(mid, server=monster.server_priority)
                    for exc in self.get_monster_exchange_models(monster)
                    for mid in exc.required_monster_ids}
        if stars is not None:
            monsters = {m for m in monsters if m.rarity == stars}
        return len({m for m in monsters for s in m.all_series if s.series_id == 34}) > 1

    def material_of_ids(self, monster: MonsterModel) -> List[int]:
        return sorted(self._get_edges(monster, 'material_of'))

    def material_of_monsters(self, monster: MonsterModel) -> List[MonsterModel]:
        return [self.get_monster(m, server=monster.server_priority)
                for m in self.material_of_ids(monster)]

    def monster_difference(self, monster: MonsterModel, server) -> MonsterDifference:
        return monster.get_difference(self.get_monster(monster.monster_id, server=server))

    def monster_is_discrepant(self, monster: MonsterModel) -> bool:
        return any((md := self.monster_difference(monster, server)) and not md.existance
                   for server in SERVERS)

    def debug_validate_id(self, monster_id: int) -> Optional[int]:
        if self.debug_monster_ids is None or monster_id in self.debug_monster_ids:
            return monster_id
