from typing import List, Optional

from pydantic import BaseModel

from api.responses.active_skill import ActiveSkill
from api.responses.awakening import Awakening
from api.responses.leader_skill import LeaderSkill
from api.responses.series import Series
from api.responses.stat_values import StatValues
from dbcog.models.enum_types import MonsterType, Attribute
from dbcog.models.monster_model import MonsterModel


class MonsterResponse(BaseModel):
    active_skill: ActiveSkill
    active_skill_id: int
    all_series: List[Series]
    atk_max: int
    atk_min: int
    atk_scale: int
    attr1: Optional[Attribute]
    attr2: Optional[Attribute]
    awakenings: List[Awakening]
    base_evo_id: int
    bgm_id: Optional[int]
    buy_mp: Optional[int]
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
    series: Series
    series_id: int
    server_priority: str
    stat_values: StatValues
    superawakening_count: int
    type1: Optional[MonsterType]
    type2: Optional[MonsterType]
    type3: Optional[MonsterType]
    types: List[MonsterType]
    unoverridden_name_en: str
    voice_id_jp: Optional[int]
    voice_id_na: Optional[int]

    @staticmethod
    def from_model(m: MonsterModel):
        return MonsterResponse(
            active_skill=ActiveSkill.from_model(m.active_skill),
            active_skill_id=m.active_skill_id,
            all_series=[Series.from_model(a) for a in m.all_series],
            atk_max=m.atk_max,
            atk_min=m.atk_min,
            atk_scale=m.atk_scale,
            attr1=m.attr1,
            attr2=m.attr2,
            awakenings=[Awakening.from_model(a) for a in m.awakenings],
            base_evo_id=m.base_evo_id,
            bgm_id=m.bgm_id,
            buy_mp=m.buy_mp,
            collab_id=m.collab_id,
            cost=m.cost,
            evo_gem_id=m.evo_gem_id,
            exp=m.exp,
            fodder_exp=m.fodder_exp,
            group_id=m.group_id,
            has_animation=m.has_animation,
            has_hqimage=m.has_hqimage,
            hp_max=m.hp_max,
            hp_min=m.hp_min,
            hp_scale=m.hp_scale,
            in_mpshop=m.in_mpshop,
            in_pem=m.in_pem,
            in_rem=m.in_rem,
            in_vem=m.in_vem,
            is_equip=m.is_equip,
            is_farmable=m.is_farmable,
            is_inheritable=m.is_inheritable,
            is_stackable=m.is_stackable,
            latent_slots=m.latent_slots,
            leader_skill=LeaderSkill.from_model(m.leader_skill),
            leader_skill_id=m.leader_skill_id,
            level=m.level,
            limit_mult=m.limit_mult,
            monster_id=m.monster_id,
            monster_no_jp=m.monster_no_jp,
            monster_no_kr=m.monster_no_kr,
            monster_no_na=m.monster_no_na,
            name_en=m.name_en,
            name_en_override=m.name_en_override,
            name_ja=m.name_ja,
            name_ko=m.name_ko,
            on_jp=m.on_jp,
            on_kr=m.on_kr,
            on_na=m.on_na,
            orb_skin_id=m.orb_skin_id,
            rarity=m.rarity,
            rcv_max=m.rcv_max,
            rcv_min=m.rcv_min,
            rcv_scale=m.rcv_scale,
            reg_date=str(m.reg_date),
            roma_subname=m.roma_subname,
            sell_gold=m.sell_gold,
            sell_mp=m.sell_mp,
            series=Series.from_model(m.series),
            series_id=m.series_id,
            server_priority=m.server_priority.name,
            stat_values=StatValues(**m.stat_values),
            superawakening_count=m.superawakening_count,
            type1=m.type1,
            type2=m.type2,
            type3=m.type3,
            types=m.types,
            unoverridden_name_en=m.unoverridden_name_en,
            voice_id_jp=m.voice_id_jp,
            voice_id_na=m.voice_id_na,
        )
