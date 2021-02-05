from typing import List, TYPE_CHECKING, Optional

from padinfo.common.config import UserConfig
from padinfo.core.id import perform_mats_query
from padinfo.view_state.base import ViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class MaterialsViewState(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 mats: List["MonsterModel"], usedin: List["MonsterModel"], gemid: Optional[str],
                 gemusedin: List["MonsterModel"], skillups: List["MonsterModel"], skillup_evo_count: int, link: str,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=extra_state)
        self.link = link
        self.skillup_evo_count = skillup_evo_count
        self.skillups = skillups
        self.gemusedin = gemusedin
        self.mats = mats
        self.usedin = usedin
        self.gemid = gemid
        self.query = query
        self.monster = monster
        self.color = color

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'query': self.query,
            'resolved_monster_id': self.monster.monster_id
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']

        original_author_id = ims['original_author_id']

        menu_type = ims['menu_type']

        query = ims.get('query') or raw_query

        monster, mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link = await perform_mats_query(dgcog, query, user_config.beta_id3)

        return MaterialsViewState(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                                  mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, extra_state=ims)
