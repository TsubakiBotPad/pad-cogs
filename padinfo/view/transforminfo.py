from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from discordmenu.embed.text import Text, BoldText

from padinfo.common.emoji_map import get_awakening_emoji, get_emoji
from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer
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


class TransformInfoView:
    @staticmethod
    def embed(base_m: "MonsterModel", m: "MonsterModel", color):
        active_skill = base_m.active_skill
        base_cd = (" (Base: {} -> {})".format(active_skill.turn_max, active_skill.turn_min)
            if active_skill else 'None')

        fields = [
            EmbedField(
                '/'.join(['{}'.format(t.name) for t in m.types]),
                Box(
                    IdView.awakenings_row(m),
                    base_info(base_m)
                ),
            ),
            EmbedField(
                IdView.stats_header(m).to_markdown(),
                IdView.stats(m),
                inline=True
            ),
            EmbedField(
                IdView.active_skill_header(m).to_markdown() + base_cd,
                Text(m.active_skill.desc if m.active_skill else 'None')
            ),
            EmbedField(
                IdView.leader_skill_header(m).to_markdown(),
                Text(m.leader_skill.desc if m.leader_skill else 'None')
            )
        ]

        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=puzzledragonx(m)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m)),
            embed_footer=pad_info_footer(),
            embed_fields=fields
        )
