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

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


# stole a lot directly from ./id.py. code duplication?
def _get_awakening_text(awakening: "AwakeningModel"):
    return get_awakening_emoji(awakening.awoken_skill_id, awakening.name)

def _killer_latent_emoji(latent_name: str):
    return get_emoji('latent_killer_{}'.format(latent_name.lower()))

def base_info(m: "MonsterModel"):
    if len(m.awakenings) == 0:
        return Box(Text('No Awakenings'))

    normal_awakenings = len(m.awakenings) - m.superawakening_count
    normal_awakenings_emojis = [_get_awakening_text(a) for a in m.awakenings[:normal_awakenings]]
    super_awakenings_emojis = [_get_awakening_text(a) for a in m.awakenings[normal_awakenings:]]

    killers_text = 'Any' if 'Any' in m.killers else ' '.join([_killer_latent_emoji(k) for k in m.killers])

    return Box(
        Box(
            '\N{DOWN-POINTING RED TRIANGLE}',
            *[Text(e) for e in normal_awakenings_emojis],
            delimiter=' '),
        Box(
            Text(get_emoji('sa_questionmark')),
            *[Text(e) for e in super_awakenings_emojis],
            delimiter=' ') if len(super_awakenings_emojis) > 0 else None,
        Box(
            BoldText('Available killers: '),
            Text(killers_text),
            delimiter=' '
        )
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
                    IdView.awakenings_row(t_mon),
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
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=puzzledragonx(m)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(t_mon)),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields
        )
