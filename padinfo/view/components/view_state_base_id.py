import abc
from typing import TYPE_CHECKING, List

from discordmenu.embed.control import EmbedControl

from padinfo.common.config import UserConfig
from padinfo.view.common import get_monster_from_ims

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class ViewStateBaseId:
    def __init__(self, original_author_id, menu_type, raw_query, query, color, monster: "MonsterModel",
                 alt_monsters: List["MonsterModel"],
                 use_evo_scroll: bool = True,
                 reaction_list: List[str] = None,
                 extra_state=None):
        self.alt_monsters = alt_monsters
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
            'reaction_list': self.reaction_list,
        }
        ret.update(self.extra_state)
        return ret

    @classmethod
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        monster = await get_monster_from_ims(dgcog, ims)

        alt_monsters = cls.get_alt_monsters(dgcog, monster)

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')

        return cls(original_author_id, menu_type, raw_query, query, user_config.color, monster, alt_monsters,
                   use_evo_scroll=use_evo_scroll, reaction_list=reaction_list,
                   extra_state=ims)

    @abc.abstractmethod
    def control(self):
        pass

    @classmethod
    def get_alt_monsters(cls, dgcog, monster):
        db_context = dgcog.database
        alt_monsters = sorted({*db_context.graph.get_alt_monsters_by_id(monster.monster_no)},
                              key=lambda x: x.monster_id)
        return alt_monsters
