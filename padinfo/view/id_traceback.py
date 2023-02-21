from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedField, EmbedMain
from discordmenu.embed.text import LabeledText
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.tsubaki.custom_emoji import get_attribute_emoji_by_monster
from tsutils.tsubaki.monster_header import MonsterHeader

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class IdTracebackViewProps:
    def __init__(self, monster: "MonsterModel", score: float, name_tokens: str,
                 modifier_tokens: str, lower_priority_monsters: str):
        self.lower_priority_monsters = lower_priority_monsters
        self.modifier_tokens = modifier_tokens
        self.name_tokens = name_tokens
        self.score = score
        self.monster = monster


class IdTracebackView:
    VIEW_TYPE = 'IdTraceback'

    @staticmethod
    def embed(state: ClosableEmbedViewState, props: IdTracebackViewProps):
        return EmbedView(
            EmbedMain(
                color=state.qs.embedcolor,
                title=MonsterHeader.menu_title(props.monster, use_emoji=True),
                description=Box(LabeledText('Total score', str(round(props.score, 2))))
            ),
            embed_fields=[
                EmbedField('Matched Name Tokens', Box(props.name_tokens)),
                EmbedField('Matched Modifier Tokens', Box(props.modifier_tokens)),
                EmbedField('Equally-scoring matches', Box(props.lower_priority_monsters)),
            ],
            embed_footer=embed_footer_with_state(state),
        )
