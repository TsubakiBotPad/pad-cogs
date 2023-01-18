from collections import Counter
from typing import Collection, TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedThumbnail, EmbedField
from discordmenu.embed.text import LabeledText
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.tsubaki.links import MonsterImage

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel

ORDINAL_WORDS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth']


class ShowStatsViewProps:
    def __init__(self, total: Collection["MonsterModel"], adj: Collection["MonsterModel"],
                 you: Collection["MonsterModel"], valid: Collection["MonsterModel"],
                 most_common: "MonsterModel"):
        self.valid = valid
        self.total = total
        self.adj = adj
        self.you = you
        self.most_commmon = most_common


class ShowStatsView:
    VIEW_TYPE = 'ShowStats'

    MAX_EXPANDED_RESULTS = 6

    @staticmethod
    def get_count(arr: Collection["MonsterModel"], *elements: "MonsterModel") -> str:
        if not arr:
            return "N/A"
        count = sum(1 for m in arr if m in elements)
        if count == 0:
            return "0"
        return f"{round(100*count/len(arr), 3)}%"

    @classmethod
    def embed(cls, state: ClosableEmbedViewState, props: ShowStatsViewProps):
        fields = []
        for mon, c in Counter(props.valid).most_common(
                cls.MAX_EXPANDED_RESULTS if len(props.valid) == cls.MAX_EXPANDED_RESULTS
                else cls.MAX_EXPANDED_RESULTS-1):
            fields.append(EmbedField(mon.name_en, Box(
                LabeledText("Net", ShowStatsView.get_count(props.total, mon)),
                LabeledText("Adj", ShowStatsView.get_count(props.adj, mon)),
                LabeledText("You", ShowStatsView.get_count(props.you, mon))
            ), inline=True))
        if len(props.valid) > cls.MAX_EXPANDED_RESULTS:
            fields.append(EmbedField("... & More",
                                     Box(f"+ {len(props.valid)-cls.MAX_EXPANDED_RESULTS-1} more monsters"),
                                     inline=True))

        return EmbedView(
            EmbedMain(
                color=state.query_settings.embedcolor,
                title=f"AdPEM Data for query: {state.raw_query}",
                description=Box(
                    LabeledText("Net", ShowStatsView.get_count(props.total, *props.valid)),
                    LabeledText("Adj", ShowStatsView.get_count(props.adj, *props.valid)),
                    LabeledText("You", ShowStatsView.get_count(props.you, *props.valid))
                ),
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(props.most_commmon.monster_id)),
            embed_fields=fields,
            embed_footer=embed_footer_with_state(state, qs=state.query_settings)
        )
