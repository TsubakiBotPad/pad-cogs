from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedAuthor, EmbedField, EmbedMain
from discordmenu.embed.text import Text, BlockText
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.external_links import puzzledragonx
from padinfo.core.button_info import button_info, LIMIT_BREAK_LEVEL
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class ButtonInfoViewProps:
    def __init__(self, monster: "MonsterModel", info):
        self.monster = monster
        self.info = info


def get_max_level(monster):
    level_text = str(LIMIT_BREAK_LEVEL) if monster.limit_mult != 0 else 'Max ({})'.format(monster.level)
    return 'Lv. {}'.format(level_text)


def get_max_stats_without_latents(info):
    return BlockText(
        Box(
            Text('Base:    {}'.format(int(round(info.main_damage)))),
            Text('Subattr: {}'.format(int(round(info.sub_damage)))),
            Text('Total:   {}'.format(int(round(info.total_damage))))
        )
    )


def get_120_stats_without_latents(info):
    return BlockText(
        Box(
            Text('Base:    {}'.format(int(round(info.main_slb_damage)))),
            Text('Subattr: {}'.format(int(round(info.sub_slb_damage)))),
            Text('Total:   {}'.format(int(round(info.total_slb_damage))))
        )
    )


def get_max_stats_with_latents(info):
    return BlockText(
        Box(
            Text('Base:    {}'.format(int(round(info.main_damage_with_atk_latent)))),
            Text('Subattr: {}'.format(int(round(info.sub_damage_with_atk_latent)))),
            Text('Total:   {}'.format(int(round(info.total_damage_with_atk_latent))))
        )
    )


def get_120_stats_with_latents(info):
    return BlockText(
        Box(
            Text('Base:    {}'.format(int(round(info.main_damage_with_slb_atk_latent)))),
            Text('Subattr: {}'.format(int(round(info.sub_damage_with_slb_atk_latent)))),
            Text('Total:   {}'.format(int(round(info.total_damage_with_slb_atk_latent))))
        )
    )


class ButtonInfoView:
    VIEW_TYPE = 'ButtonInfo'

    @staticmethod
    def embed(state, props: ButtonInfoViewProps):
        monster = props.monster
        info = props.info

        fields = [
            EmbedField(
                get_max_level(monster),
                Box(
                    Text('Without Latents'),
                    # avoid whitespace after code block
                    Box(
                        get_max_stats_without_latents(info),
                        Text('With Latents (Atk+)'),
                        delimiter=''
                    ),
                    get_max_stats_with_latents(info)
                ),
                inline=True
            ),
            EmbedField(
                'Lv. 120',
                Box(
                    Text('Without Latents'),
                    # avoid whitespace after code block
                    Box(
                        get_120_stats_without_latents(info),
                        Text('With Latents (Atk++)'),
                        delimiter=''
                    ),
                    get_120_stats_with_latents(info)
                ),
                inline=True
            ) if monster.limit_mult != 0 else None,
            EmbedField(
                'Common Buttons - {}'.format(get_max_level(monster)),
                Box(
                    Text('*Inherits are assumed to be the max possible level (up to 110) and +297.*'),
                    # janky, but python gives DeprecationWarnings when using \* in a regular string
                    Text(r'*\* = on-color stat bonus applied*'),
                    Text('Card Button Damage'),
                    # done this way to not have the whitespace after code block
                    Box(
                        BlockText(info.card_btn_str),
                        Text('Team Button Contribution'),
                        delimiter=''
                    ),
                    BlockText(info.team_btn_str)
                )
            )
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                description='(Co-op mode)'
            ),
            embed_author=EmbedAuthor(
                MonsterHeader.long_v2(monster).to_markdown(),
                puzzledragonx(monster),
                MonsterImage.icon(monster)
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
