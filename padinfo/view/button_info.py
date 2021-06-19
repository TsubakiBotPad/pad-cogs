from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedAuthor, EmbedField, EmbedMain
from discordmenu.embed.text import Text, BlockText
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.external_links import puzzledragonx
from padinfo.core.button_info import button_info
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class ButtonInfoViewProps:
    def __init__(self, monster: "MonsterModel", info):
        self.monster = monster
        self.info = info


def get_stats_without_latents(info):
    return BlockText(
        Box(
            Text('Base:    {}'.format(int(round(info.main_damage)))),
            Text('Subattr: {}'.format(int(round(info.sub_damage)))),
            Text('Total:   {}'.format(int(round(info.total_damage))))
        )
    )


def get_stats_with_latents(info):
    return BlockText(
        Box(
            Text('Base:    {}'.format(int(round(info.main_damage_with_atk_latent)))),
            Text('Subattr: {}'.format(int(round(info.sub_damage_with_atk_latent)))),
            Text('Total:   {}'.format(int(round(info.total_damage_with_atk_latent))))
        )
    )


class ButtonInfoView:
    VIEW_TYPE = 'ButtonInfo'

    @staticmethod
    def embed(state, props: ButtonInfoViewProps):
        monster = props.monster
        info = props.info

        fields = [
            EmbedField('Without Latents', get_stats_without_latents(info)),
            EmbedField('With Latents', get_stats_with_latents(info)),
            EmbedField(
                'Common Buttons',
                Box(
                    Text('*Inherits are assumed to be the max possible level (up to 110) and +297.*'),
                    Text('*\* = on-color stat bonus applied*'),
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
