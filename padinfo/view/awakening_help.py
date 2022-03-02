from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField, EmbedAuthor
from discordmenu.embed.text import Text
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.tsubaki.custom_emoji import get_awakening_emoji
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.common import get_awoken_skill_description

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.models.awakening_model import AwakeningModel

ORDINAL_WORDS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth']


class AwakeningHelpViewProps:
    def __init__(self, monster: "MonsterModel"):
        self.monster = monster


def _get_short_desc(prev_index: int, awakening: "AwakeningModel"):
    emoji_text = get_awakening_emoji(awakening.awoken_skill_id, awakening.name)
    return Box(
        Text(emoji_text),
        Text('[Same as {} awakening]'.format(ORDINAL_WORDS[prev_index])),
        delimiter=' '
    )


def _get_all_awakening_descs(awakening_list):
    appearances = {}
    awakening_descs = []
    for index, awakening in enumerate(awakening_list):
        if awakening.name not in appearances:
            appearances[awakening.name] = index
            awakening_descs.append(get_awoken_skill_description(awakening.awoken_skill))
        else:
            awakening_descs.append(_get_short_desc(appearances[awakening.name], awakening))

    return Box(*awakening_descs)


def get_normal_awakenings(monster: "MonsterModel"):
    normal_awakening_count = len(monster.awakenings) - monster.superawakening_count
    normal_awakenings = monster.awakenings[:normal_awakening_count]
    return _get_all_awakening_descs(normal_awakenings)


def get_super_awakenings(monster: "MonsterModel"):
    normal_awakening_count = len(monster.awakenings) - monster.superawakening_count
    super_awakenings = monster.awakenings[normal_awakening_count:]
    return _get_all_awakening_descs(super_awakenings)


class AwakeningHelpView:
    VIEW_TYPE = 'AwakeningHelp'

    @staticmethod
    def embed(state, props: AwakeningHelpViewProps):
        monster = props.monster

        fields = [
            EmbedField('Normal Awakenings', get_normal_awakenings(monster)),
            EmbedField('Super Awakenings', get_super_awakenings(monster))
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                description='This monster has no awakenings.' if not monster.awakenings else ''
            ),
            embed_author=EmbedAuthor(
                MonsterHeader.menu_title(monster).to_markdown(),
                # TODO: add query_settings
                MonsterLink.header_link(monster),
                MonsterImage.icon(monster.monster_id)
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
