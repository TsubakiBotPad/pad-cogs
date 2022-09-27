from typing import List, Optional

from pydantic import BaseModel

from api.responses.active_skill import ActiveSkill
from api.responses.awakening import Awakening
from api.responses.leader_skill import LeaderSkill
from api.responses.series import SeriesModel
from api.responses.stat_values import StatValues


class MonsterResponse(BaseModel):
    active_skill: ActiveSkill
    active_skill_id: int
    all_series: List[SeriesModel]
    atk_max: int
    atk_min: int
    atk_scale: int
    attr1: int
    attr2: int
    awakenings: List[Awakening]
    base_evo_id: int
    buy_mp: int
    collab_id: int
    cost: int
    evo_gem_id: Optional[int]
    exp: int
    fodder_exp: int
    group_id: int
    has_animation: bool
    has_hqimage: bool
    hp_max: int
    hp_min: int
    hp_scale: int
    in_mpshop: bool
    in_pem: bool
    in_rem: bool
    in_vem: bool
    is_equip: bool
    is_farmable: bool
    is_inheritable: bool
    is_stackable: bool
    latent_slots: int
    leader_skill: LeaderSkill
    leader_skill_id: int
    level: int
    limit_mult: int
    monster_id: int
    monster_no_jp: int
    monster_no_kr: int
    monster_no_na: int
    name_en: str
    name_en_override: Optional[str]
    name_ja: str
    name_ko: str
    on_jp: bool
    on_kr: bool
    on_na: bool
    orb_skin_id: Optional[int]
    rarity: int
    rcv_max: int
    rcv_min: int
    rcv_scale: int
    reg_date: str
    roma_subname: Optional[str]
    sell_gold: int
    sell_mp: int
    series: SeriesModel
    series_id: int
    server_priority: str
    stat_values: StatValues
    superawakening_count: int
    type1: int
    type2: int
    type3: int
    types: List[int]
    unoverridden_name_en: str
    voice_id_jp: Optional[int]
    voice_id_na: Optional[int]
