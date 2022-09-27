from pydantic import BaseModel


class SeriesModel(BaseModel):
    series_id: int
    name_ja: str
    name_en: str
    name_ko: str
    series_type: str
