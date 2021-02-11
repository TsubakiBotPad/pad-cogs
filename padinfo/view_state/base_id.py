from typing import TYPE_CHECKING, List

from padinfo.common.config import UserConfig
from padinfo.view_state.common import get_monster_from_ims, get_reaction_list_from_ims

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class ViewStateBaseId:
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 use_evo_scroll: bool = True,
                 reaction_list: List[str] = None,
                 extra_state=None):
        self.extra_state = extra_state or {}
        self.menu_type = menu_type
        self.original_author_id = original_author_id
        self.raw_query = raw_query
        self.reaction_list = reaction_list
        self.color = color
        self.monster = monster
        self.query = query
        self.use_evo_scroll = use_evo_scroll

    def serialize(self):
        ret = {
            'raw_query': self.raw_query,
            'menu_type': self.menu_type,
            'original_author_id': self.original_author_id,
            'query': self.query,
            'resolved_monster_id': self.monster.monster_id,
            'use_evo_scroll': str(self.use_evo_scroll),
            'reaction_list': ','.join(self.reaction_list) if self.reaction_list else None,
        }
        ret.update(self.extra_state)
        return ret

    @classmethod
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict):
        monster = await get_monster_from_ims(dgcog, user_config, ims)

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        menu_type = ims['menu_type']
        reaction_list = get_reaction_list_from_ims(ims)

        return cls(original_author_id, menu_type, raw_query, query, user_config.color, monster,
                   use_evo_scroll=use_evo_scroll, reaction_list=reaction_list,
                   extra_state=ims)
