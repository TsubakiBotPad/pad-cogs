from typing import List


class ViewStateBase:
    def __init__(self, original_author_id, menu_type, raw_query, extra_state=None, reaction_list: List = None):
        self.extra_state = extra_state or {}
        self.menu_type = menu_type
        self.original_author_id = original_author_id
        self.raw_query = raw_query
        self.reaction_list = reaction_list

    def serialize(self):
        ret = {
            'raw_query': self.raw_query,
            'menu_type': self.menu_type,
            'original_author_id': self.original_author_id,
        }
        ret.update(self.extra_state)
        if self.reaction_list is not None:
            ret['reaction_list'] = self.reaction_list
        return ret
