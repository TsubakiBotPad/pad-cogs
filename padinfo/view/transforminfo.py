from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from discordmenu.embed.text import Text, BoldText

from padinfo.common.emoji_map import get_awakening_emoji, get_emoji
from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.id import IdView
from padinfo.view_state.id import IdViewState
from padinfo.view_state.transforminfo import TransformInfoViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


def base_info(m: "MonsterModel"):
    return Box(
        Box(
            '\N{DOWN-POINTING RED TRIANGLE}',
            IdView.normal_awakenings_row(m) if len(m.awakenings) != 0 else Box(Text('No Awakenings')),
            delimiter=' '
        ),
        IdView.super_awakenings_row(m),
        # the transform base of the base is the same
        IdView.killers_row(m, m)
    )

def base_skill(m: "MonsterModel"):
    active_skill = m.active_skill
    return (" (Base: {} -> {})".format(active_skill.turn_max, active_skill.turn_min) if active_skill
        else 'None')


class TransformInfoView:
    @staticmethod
    def embed(state: TransformInfoViewState):
        b_mon = state.b_mon
        t_mon = state.t_mon

        fields = [
            EmbedField(
                '/'.join(['{}'.format(t.name) for t in t_mon.types]),
                Box(
                    IdView.normal_awakenings_row(t_mon),
                    base_info(b_mon)
                ),
            ),
            EmbedField(
                'Fresh and cool information',
                IdView.misc_info(t_mon, state.true_evo_type_raw, state.acquire_raw, state.base_rarity),
                inline=True
            ),
            EmbedField(
                IdView.stats_header(t_mon).to_markdown(),
                IdView.stats(t_mon),
                inline=True
            ),
            EmbedField(
                IdView.active_skill_header(t_mon).to_markdown() + base_skill(b_mon),
                Text(t_mon.active_skill.desc if t_mon.active_skill else 'None')
            ),
            EmbedField(
                IdView.leader_skill_header(t_mon).to_markdown(),
                Text(t_mon.leader_skill.desc if t_mon.leader_skill else 'None')
            )
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_v2(t_mon).to_markdown(),
                url=puzzledragonx(t_mon)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(t_mon)),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields
        )
