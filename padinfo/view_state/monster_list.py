from typing import TYPE_CHECKING, List

from padinfo.common.config import UserConfig
from padinfo.pane_names import IdMenuPaneNames
from padinfo.view_state.base import ViewStateBase
from padinfo.view_state.common import get_reaction_list_from_ims

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class MonsterListViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query, query, color,
                 monster_list: List["MonsterModel"], title,
                 reaction_list=None,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query,
                         extra_state=extra_state)
        self.title = title
        self.monster_list = monster_list
        self.reaction_list = reaction_list
        self.color = color
        self.query = query

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': IdMenuPaneNames.id,
            'title': self.title,
            'monster_list': [str(m.monster_no) for m in self.monster_list],
            'reaction_list': ','.join(self.reaction_list) if self.reaction_list else None,
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        monster_list = [dgcog.database.graph.get_monster(int(m)) for m in ims['monster_list']]
        title = ims['title']

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = get_reaction_list_from_ims(ims)

        return MonsterListViewState(original_author_id, menu_type, raw_query, query, user_config.color,
                                    monster_list=monster_list, title=title,
                                    reaction_list=reaction_list,
                                    extra_state=ims)
