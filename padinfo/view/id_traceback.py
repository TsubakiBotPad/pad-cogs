from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.text import LabeledText
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.emoji_map import get_attribute_emoji_by_monster

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class IdTracebackViewProps:
    def __init__(self, monster: "MonsterModel", score: int, name_tokens: str,
                 modifier_tokens: str, lower_priority_monsters: str):
        self.lower_priority_monsters = lower_priority_monsters
        self.modifier_tokens = modifier_tokens
        self.name_tokens = name_tokens
        self.score = score
        self.monster = monster


def get_title(monster: "MonsterModel"):
    return f"{get_attribute_emoji_by_monster(monster)} {monster.name_en} ({monster.monster_id})"


def get_description(score: int):
    return Box(
        LabeledText(
            'Total score',
            str(round(score, 2))
        )
    )


class IdTracebackView:
    VIEW_TYPE = 'IdTraceback'

    @staticmethod
    def embed(state, props: IdTracebackViewProps):
        fields = [
            EmbedField('Matched Name Tokens', Box(props.name_tokens)),
            EmbedField('Matched Modifier Tokens', Box(props.modifier_tokens)),
            EmbedField('Equally-scoring matches', Box(props.lower_priority_monsters)),
        ]
        return EmbedView(
            EmbedMain(
                color=state.color,
                title=get_title(props.monster),
                description=get_description(props.score)
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields)
