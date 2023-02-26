from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedAuthor, EmbedField, EmbedMain
from discordmenu.embed.text import Text
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.tsubaki.custom_emoji import get_awakening_emoji
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.common import get_awoken_skill_description

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.models.awakening_model import AwakeningModel

ORDINAL_WORDS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth']


class AwakeningHelpViewProps:
    def __init__(self, monster: "MonsterModel", token_map: dict):
        self.monster = monster

        # this is the list of allowed modifiers from token_mappings dbcog file (cannot import it bc redbot rules)
        self.token_map = {}
        for k in token_map.keys():
            self.token_map[k.value] = token_map[k]


def _get_repeated_desc(prev_index: int, awakening: "AwakeningModel"):
    emoji_text = get_awakening_emoji(awakening.awoken_skill_id, awakening.name)
    return Box(
        Text(emoji_text),
        Text('[Same as {} awakening]'.format(ORDINAL_WORDS[prev_index])),
        delimiter=' '
    )


def _get_all_awakening_descs(awakening_list, show_help, token_map):
    appearances = {}
    awakening_descs = []
    for index, awakening in enumerate(awakening_list):
        if awakening.name not in appearances:
            appearances[awakening.name] = index
            awakening_descs.append(
                get_awoken_skill_description(
                    awakening.awoken_skill, show_help=show_help, token_map=token_map))
        else:
            awakening_descs.append(_get_repeated_desc(appearances[awakening.name], awakening))

    return Box(*awakening_descs)


def get_normal_awakenings(monster: "MonsterModel", show_help: bool, token_map: dict):
    normal_awakening_count = len(monster.awakenings) - monster.superawakening_count
    normal_awakenings = monster.awakenings[:normal_awakening_count]
    return _get_all_awakening_descs(normal_awakenings, show_help, token_map)


def get_super_awakenings(monster: "MonsterModel", show_help: bool, token_map: dict):
    normal_awakening_count = len(monster.awakenings) - monster.superawakening_count
    super_awakenings = monster.awakenings[normal_awakening_count:]
    return _get_all_awakening_descs(super_awakenings, show_help, token_map)


class AwakeningHelpView:
    VIEW_TYPE = 'AwakeningHelp'

    @staticmethod
    def embed(state: ClosableEmbedViewState, props: AwakeningHelpViewProps):
        monster = props.monster
        show_help = state.qs.showhelp.value
        token_map = props.token_map
        fields = [
            EmbedField('Normal Awakenings', get_normal_awakenings(monster, show_help, token_map)),
            EmbedField('Super Awakenings', get_super_awakenings(monster, show_help, token_map))
        ]

        return EmbedView(
            EmbedMain(
                color=state.qs.embedcolor,
                description='This monster has no awakenings.' if not monster.awakenings else ''
            ),
            embed_author=EmbedAuthor(
                MonsterHeader.menu_title(monster).to_markdown(),
                MonsterLink.header_link(monster, qs=state.qs),
                MonsterImage.icon(monster.monster_id)
            ),
            embed_footer=embed_footer_with_state(state, qs=state.qs),
            embed_fields=fields
        )
