from typing import List

from discordmenu.embed.view_state import ViewState


class ViewStateBase(ViewState):
    def __init__(self, original_author_id, menu_type, raw_query, extra_state=None, reaction_list: List = None):
        self.reaction_list = reaction_list
        super().__init__(original_author_id=original_author_id, menu_type=menu_type, raw_query=raw_query,
                         extra_state=extra_state)

    def serialize(self):
        ret = super().serialize()
        if self.reaction_list is not None:
            ret['reaction_list'] = self.reaction_list
        return ret
