from collections import Counter
from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedThumbnail, EmbedField
from discordmenu.embed.text import LabeledText
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.closable_embed import ClosableEmbedViewState

from padinfo.view.components.monster.image import MonsterImage

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel

ORDINAL_WORDS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth']


class ShowStatsViewProps:
    def __init__(self, total: List["MonsterModel"], adj: List["MonsterModel"],
                 you: List["MonsterModel"], valid: List["MonsterModel"]):
        self.valid = valid
        self.total = total
        self.adj = adj
        self.you = you


class ShowStatsView:
    VIEW_TYPE = 'ShowStats'

    @staticmethod
    def get_count(arr: List["MonsterModel"], *elements: "MonsterModel") -> str:
        if not arr:
            return "N/A"
        count = sum(1 for m in arr if m in elements)
        if count == 0:
            return "0"
        return f"{round(100*count/len(arr), 3)}%"

    @staticmethod
    def embed(state: ClosableEmbedViewState, props: ShowStatsViewProps):

        fields = []
        for mon, c in Counter(props.valid).most_common(6 if len(props.valid) == 6 else 5):
            fields.append(EmbedField(mon.name_en, Box(
                LabeledText("Net", ShowStatsView.get_count(props.total, mon)),
                LabeledText("Adj", ShowStatsView.get_count(props.adj, mon)),
                LabeledText("You", ShowStatsView.get_count(props.you, mon))
            ), inline=True))
        if len(set(props.valid)) > 6:
            fields.append(EmbedField("... & More", Box(f"+ {len(props.valid) - 5} more monsters"), inline=True))

        return EmbedView(
            EmbedMain(
                title=f"AdPEM Data for query: {state.raw_query}",
                description=Box(
                    LabeledText("Net", ShowStatsView.get_count(props.total, *set(props.valid))),
                    LabeledText("Adj", ShowStatsView.get_count(props.adj, *set(props.valid))),
                    LabeledText("You", ShowStatsView.get_count(props.you, *set(props.valid)))
                )
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(Counter(props.valid).most_common(1)[0][0])),
            embed_fields=fields,
            embed_footer=embed_footer_with_state(state)
        )

