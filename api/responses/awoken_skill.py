from pydantic import BaseModel


class AwokenSkill(BaseModel):
    awoken_skill_id: int
    name_ja: str
    name_en: str
    name_ko: str
    name: str
    desc_ja: str
    desc_en: str
    desc_ja: str
    desc_ko: str
    adj_hp: int
    adj_atk: int
    adj_rcv: int
