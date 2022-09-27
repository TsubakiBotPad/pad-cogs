from pydantic import BaseModel

from dbcog.models.series_model import SeriesModel


class Series(BaseModel):
    series_id: int
    name_ja: str
    name_en: str
    name_ko: str
    series_type: str

    @staticmethod
    def from_model(m: SeriesModel):
        return Series(
            series_id=m.series_id,
            name_ja=m.name_ja,
            name_en=m.name_en,
            name_ko=m.name_ko,
            series_type=m.series_type,
        )
