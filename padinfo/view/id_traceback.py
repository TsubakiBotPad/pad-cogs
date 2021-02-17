from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.text import LabeledText
from discordmenu.embed.view import EmbedView

from padinfo.common.emoji_map import get_attribute_emoji_by_monster
from padinfo.view.components.base import pad_info_footer_with_state

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


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
    def embed(state, monster: "MonsterModel" = None, score: int = None, name_tokens: str = None,
              modifier_tokens: str = None, lower_priority_monsters: str = None):
        fields = [
            EmbedField('Matched Name Tokens', Box(name_tokens)),
            EmbedField('Matched Modifier Tokens', Box(modifier_tokens)),
            EmbedField('Equally-scoring matches', Box(lower_priority_monsters)),
        ]
        return EmbedView(
            EmbedMain(
                color=state.color,
                title=get_title(monster),
                description=get_description(score)
            ),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields)
