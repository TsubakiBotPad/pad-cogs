from pydantic import BaseModel

from dbcog.models.awoken_skill_model import AwokenSkillModel


class AwokenSkill(BaseModel):
    awoken_skill_id: int
    name_ja: str
    name_en: str
    name_ko: str
    name: str
    desc_ja: str
    desc_en: str
    desc_ko: str
    adj_hp: int
    adj_atk: int
    adj_rcv: int

    @staticmethod
    def from_model(m: AwokenSkillModel):
        return AwokenSkill(
            awoken_skill_id=m.awoken_skill_id,
            name_ja=m.name_ja,
            name_en=m.name_en,
            name_ko=m.name_ko,
            name=m.name,
            desc_ja=m.desc_ja,
            desc_en=m.desc_en,
            desc_ko=m.desc_ko,
            adj_hp=m.adj_hp,
            adj_atk=m.adj_atk,
            adj_rcv=m.adj_rcv,
        )
