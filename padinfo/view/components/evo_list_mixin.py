from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from dbcog.database_context import DbContext
    from dbcog.models.monster_model import MonsterModel


class EvoListViewState:
    use_evo_scroll: bool
    alt_monster_ids: List[int]
    monster: "MonsterModel"

    def decrement_monster(self, dbcog, ims: dict):
        db_context: "DbContext" = dbcog.database
        if self.use_evo_scroll:
            index = self.alt_monster_ids.index(self.monster.monster_id)
            prev_monster_id = self.alt_monster_ids[index - 1]
        else:
            prev_monster = db_context.graph.numeric_prev_monster(self.monster)
            prev_monster_id = prev_monster.monster_id if prev_monster else None
            if prev_monster_id is None:
                ims['unsupported_transition'] = True
        ims['resolved_monster_id'] = str(prev_monster_id)

    def increment_monster(self, dbcog, ims: dict):
        db_context: "DbContext" = dbcog.database
        if self.use_evo_scroll:
            index = self.alt_monster_ids.index(self.monster.monster_id)
            if index == len(self.alt_monster_ids) - 1:
                # cycle back to the beginning of the evos list
                next_monster_id = self.alt_monster_ids[0]
            else:
                next_monster_id = self.alt_monster_ids[index + 1]
        else:
            next_monster = db_context.graph.numeric_next_monster(self.monster)
            next_monster_id = next_monster.monster_id if next_monster else None
            if next_monster_id is None:
                ims['unsupported_transition'] = True
        ims['resolved_monster_id'] = str(next_monster_id)
