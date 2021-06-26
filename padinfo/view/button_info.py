from typing import TYPE_CHECKING

import prettytable
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
    if info.main_damage_with_slb_atk_latent is None:
        table = Box(
            Text('Base:    {}'.format(int(round(info.main_damage)))),
            Text('Subattr: {}'.format(int(round(info.sub_damage)))),
            Text('Total:   {}'.format(int(round(info.total_damage))))
        )
    else:
        table = _slb_table(info, latent=False)
    return BlockText(table)


def get_stats_with_latents(info):
    if info.main_damage_with_slb_atk_latent is None:
        table = Box(
            Text('Base:    {}'.format(int(round(info.main_damage_with_atk_latent)))),
            Text('Subattr: {}'.format(int(round(info.sub_damage_with_atk_latent)))),
            Text('Total:   {}'.format(int(round(info.total_damage_with_atk_latent))))
        )
    else:
        table = _slb_table(info, latent=True)
    return BlockText(table)


def _slb_table(info, latent: bool):
    if latent:
        cols = ['', 'Max (Atk+)', '120 (Atk++)']
        main_110 = int(round(info.main_damage_with_atk_latent))
        sub_110 = int(round(info.sub_damage_with_atk_latent))
        total_110 = int(round(info.total_damage_with_atk_latent))
        main_120 = int(round(info.main_damage_with_slb_atk_latent))
        sub_120 = int(round(info.sub_damage_with_slb_atk_latent))
        total_120 = int(round(info.total_damage_with_slb_atk_latent))
    else:
        cols = ['', 'Max Level', '120']
        main_110 = int(round(info.main_damage))
        sub_110 = int(round(info.sub_damage))
        total_110 = int(round(info.total_damage))
        main_120 = int(round(info.main_slb_damage))
        sub_120 = int(round(info.sub_slb_damage))
        total_120 = int(round(info.total_slb_damage))

    tbl = prettytable.PrettyTable(cols)
    tbl.hrules = prettytable.NONE
    tbl.vrules = prettytable.NONE
    tbl.align = "l"
    tbl.add_row(['Base:', main_110, main_120])
    tbl.add_row(['Subattr:', sub_110, sub_120])
    tbl.add_row(['Total:', total_110, total_120])
    return tbl.get_string()


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
