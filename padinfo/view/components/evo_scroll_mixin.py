from typing import List, TYPE_CHECKING

from discordmenu.embed.components import EmbedField
from discordmenu.embed.text import HighlightableLinks, LinkedText

from padinfo.common.external_links import puzzledragonx

if TYPE_CHECKING:
    from dbcog.database_context import DbContext
    from dbcog.models.monster_model import MonsterModel
    from view_state_base_id import MonsterEvolution


class EvoScrollViewState:
    use_evo_scroll: bool
    alt_monster_ids: List[int]
    monster: "MonsterModel"
    alt_monsters: List["MonsterEvolution"]

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


class EvoScrollView:
    @staticmethod
    def evos_embed_field(state: EvoScrollViewState):
        field_text = "**Evos**"
        help_text = ""
        # this isn't used right now, but maybe later if discord changes the api for embed titles...?
        _help_link = "https://github.com/TsubakiBotPad/pad-cogs/wiki/Evolutions-mini-view"
        legend_parts = []
        if any(not alt_evo.evolution.reversible for alt_evo in state.alt_monsters if alt_evo.evolution):
            legend_parts.append("⌊Irreversible⌋")
        if any(alt_evo.monster.is_equip for alt_evo in state.alt_monsters):
            legend_parts.append("⌈Equip⌉")
        if legend_parts:
            help_text = ' – Help: {}'.format(" ".join(legend_parts))
        return EmbedField(
            field_text + help_text,
            HighlightableLinks(
                links=[LinkedText(EvoScrollView.alt_fmt(evo), puzzledragonx(evo.monster)) for evo in state.alt_monsters],
                highlighted=next(i for i, me in enumerate(state.alt_monsters)
                                 if state.monster.monster_id == me.monster.monster_id)
            )
        )

    @staticmethod
    def alt_fmt(evo: "MonsterEvolution"):
        if evo.monster.is_equip:
            fmt = "⌈{}⌉"
        elif not evo.evolution or evo.evolution.reversible:
            fmt = "{}"
        else:
            fmt = "⌊{}⌋"
        return fmt.format(evo.monster.monster_no_na)
