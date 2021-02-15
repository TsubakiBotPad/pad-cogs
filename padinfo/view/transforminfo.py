from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.text import Text, BoldText
from discordmenu.embed.view import EmbedView

from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.id import IdView
from padinfo.view_state.transforminfo import TransformInfoViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

BASE_EMOJI = '\N{DOWN-POINTING RED TRIANGLE}'


def base_info(m: "MonsterModel"):
    return Box(
        Box(
            BASE_EMOJI,
            IdView.normal_awakenings_row(m) if len(m.awakenings) != 0
            else Box(Text('No Awakenings')),
            delimiter=' '
        ),
        IdView.super_awakenings_row(m)
    )


def transform_skill_header(m: "MonsterModel"):
    active_skill = m.active_skill
    active_cd = '({} cd)'.format(active_skill.turn_min) if active_skill else 'None'
    return Box(
        BoldText('Active Skill'),
        BoldText(active_cd),
        delimiter=' '
    )


def base_skill(m: "MonsterModel"):
    active_skill = m.active_skill
    return (" (" + BASE_EMOJI + " "
            + "{} -> {})".format(active_skill.turn_max, active_skill.turn_min) if active_skill
            else 'None')


class TransformInfoView:
    @staticmethod
    def embed(state: TransformInfoViewState):
        base_mon = state.base_mon
        transformed_mon = state.transformed_mon

        fields = [
            EmbedField(
                '/'.join(['{}'.format(t.name) for t in transformed_mon.types]),
                Box(
                    IdView.normal_awakenings_row(transformed_mon)
                    if len(transformed_mon.awakenings) != 0 else Box(Text('No Awakenings')),
                    base_info(base_mon),
                    IdView.killers_row(transformed_mon, base_mon)
                ),
            ),
            EmbedField(
                'Card info',
                IdView.misc_info(transformed_mon, state.true_evo_type_raw, state.acquire_raw,
                                 state.base_rarity),
                inline=True
            ),
            EmbedField(
                IdView.stats_header(transformed_mon).to_markdown(),
                IdView.stats(transformed_mon),
                inline=True
            ),
            EmbedField(
                transform_skill_header(transformed_mon).to_markdown() + base_skill(base_mon),
                Text(transformed_mon.active_skill.desc if transformed_mon.active_skill else 'None')
            ),
            EmbedField(
                IdView.leader_skill_header(transformed_mon).to_markdown(),
                Text(transformed_mon.leader_skill.desc if transformed_mon.leader_skill else 'None')
            )
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_v2(transformed_mon).to_markdown(),
                url=puzzledragonx(transformed_mon)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(transformed_mon)),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields
        )
