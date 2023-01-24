from abc import abstractmethod
from typing import List, NamedTuple, Optional, TYPE_CHECKING

from discordmenu.embed.components import EmbedField
from discordmenu.embed.text import HighlightableLinks, LinkedText
from tsutils.query_settings.enums import AltEvoSort
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterLink

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.models.evolution_model import EvolutionModel


class MonsterEvolution(NamedTuple):
    monster: "MonsterModel"
    evolution: Optional["EvolutionModel"]


class EvoScrollViewState:
    alt_monster_ids: List[int]
    monster: "MonsterModel"
    alt_monsters: List["MonsterEvolution"]
    query_settings: QuerySettings

    def decrement_monster(self, dbcog, ims: dict):

        # if this ever has a side effect in the actual class, it cannot remain as a mixin!

        index = self.alt_monster_ids.index(self.monster.monster_id)
        prev_monster_id = self.alt_monster_ids[index - 1]
        ims['resolved_monster_id'] = str(prev_monster_id)

    def increment_monster(self, dbcog, ims: dict):
        index = self.alt_monster_ids.index(self.monster.monster_id)
        if index == len(self.alt_monster_ids) - 1:
            # cycle back to the beginning of the evos list
            next_monster_id = self.alt_monster_ids[0]
        else:
            next_monster_id = self.alt_monster_ids[index + 1]
        ims['resolved_monster_id'] = str(next_monster_id)

    @classmethod
    def alt_monster_order_pref(cls, dfs_alt_monsters, qs: QuerySettings):
        if qs.evosort == AltEvoSort.dfs:
            return dfs_alt_monsters
        else:
            return sorted(dfs_alt_monsters, key=lambda m: m.monster.monster_id)

    @classmethod
    def alt_monster_ids(cls, alt_monsters):
        return [m.monster.monster_id for m in alt_monsters]

    @classmethod
    def get_alt_monsters_and_evos(cls, dbcog, monster) -> List[MonsterEvolution]:
        graph = dbcog.database.graph
        alt_monsters = graph.get_alt_monsters(monster)
        return [MonsterEvolution(m, graph.get_evolution(m)) for m in alt_monsters]

    @abstractmethod
    def deserialize(self, dbcog, user_config, ims):
        ...


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
                links=[LinkedText(
                    EvoScrollView.alt_fmt(evo),
                    MonsterLink.header_link(evo.monster, state.query_settings)
                ) for evo in state.alt_monsters],
                highlighted=next(i for i, me in enumerate(state.alt_monsters)
                                 if state.monster.monster_id == me.monster.monster_id)
            )
        )

    @staticmethod
    def alt_fmt(evo: MonsterEvolution):
        if evo.monster.is_equip:
            fmt = "⌈{}⌉"
        elif not evo.evolution or evo.evolution.reversible:
            fmt = "{}"
        else:
            fmt = "⌊{}⌋"
        return fmt.format(evo.monster.monster_no_na)
