from typing import List

from padinfo.menu.monster_list import MonsterListMenuPanes, MonsterListEmoji


class ScrollMenuPanes(MonsterListMenuPanes):
    @classmethod
    def get_initial_reaction_list(cls, number_of_evos: int):
        return [MonsterListEmoji.prev_mon, MonsterListEmoji.next_mon]

    @classmethod
    def get_previous_reaction_list_num_monsters(cls, reaction_list: List):
        # we don't want any extra emojis
        return 0

    @classmethod
    def get_monster_index(cls, n: int):
        # this is unimportant because we don't use indices
        return 0
