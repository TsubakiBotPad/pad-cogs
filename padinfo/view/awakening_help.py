from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedAuthor
from discordmenu.embed.text import Text
from discordmenu.embed.view import EmbedView

from padinfo.common.emoji_map import get_awakening_emoji
from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel
    from dadguide.models.awakening_model import AwakeningModel


class AwakeningHelpViewProps:
    def __init__(self, monster: "MonsterModel"):
        self.monster = monster


def _get_awakening_desc(awakening: "AwakeningModel"):
    emoji_text = get_awakening_emoji(awakening.awoken_skill_id, awakening.name)
    # TODO
    desc = 'Awakening long description text here'
    return Box(
        Text(emoji_text),
        Text(desc),
        delimiter=' '
    )


def normal_awakenings(monster: "MonsterModel"):
    normal_awakening_count = len(monster.awakenings) - monster.superawakening_count
    awakening_descs = [_get_awakening_desc(a) for a in monster.awakenings[:normal_awakening_count]]
    return Box(*awakening_descs)


def super_awakenings(monster: "MonsterModel"):
    normal_awakening_count = len(monster.awakenings) - monster.superawakening_count
    awakening_descs = [_get_awakening_desc(a) for a in monster.awakenings[normal_awakening_count:]]
    return Box(*awakening_descs) if len(awakening_descs) > 0 else Box()


class AwakeningHelpView:
    VIEW_TYPE = 'AwakeningHelp'

    @staticmethod
    def embed(state, props: AwakeningHelpViewProps):
        monster = props.monster

        fields = [
            EmbedField('Normal Awakenings', normal_awakenings(monster)),
            EmbedField('Super Awakenings', super_awakenings(monster))
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                description='This monster has no awakenings.' if not monster.awakenings else ''
            ),
            embed_author=EmbedAuthor(
                MonsterHeader.long_v2(monster).to_markdown(),
                puzzledragonx(monster),
                MonsterImage.icon(monster)
            ),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields if monster.awakenings else None
        )
