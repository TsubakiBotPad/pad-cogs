from pydantic import BaseModel


class StatValue(BaseModel):
    min: int
    max: int
    scale: int


class StatValues(BaseModel):
    hp: StatValue
    atk: StatValue
    rcv: StatValue
