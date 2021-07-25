from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedAuthor, EmbedField, EmbedMain
from discordmenu.embed.text import Text, BlockText
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state
from tsutils.query_settings import QuerySettings

from padinfo.common.config import UserConfig
from padinfo.common.external_links import puzzledragonx
from padinfo.core.button_info import button_info, LIMIT_BREAK_LEVEL
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.components.view_state_base import ViewStateBase

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class ButtonInfoOptions:
    coop = 'Multiplayer'
    solo = 'Singleplayer'
    desktop = 'Desktop'
    mobile = 'Mobile'
    limit_break = 'Level 110'
    super_limit_break = 'Level 120'


class ButtonInfoToggles:
    # ???? is this how to do a class??
    def __init__(self, players_setting=ButtonInfoOptions.coop, device_setting=ButtonInfoOptions.desktop,
                 max_level_setting=ButtonInfoOptions.limit_break):
        self.players = players_setting
        self.device = device_setting
        self.max_level = max_level_setting


class ButtonInfoViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query, color, display_options: ButtonInfoToggles,
                 monster: "MonsterModel", info, query_settings: QuerySettings, reaction_list: List[str] = None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None, reaction_list=reaction_list)
        self.color = color
        self.display_options = display_options
        self.monster = monster
        self.info = info
        self.query_settings = query_settings

    def serialize(self):
        ret = super().serialize()
        ret.update({
            # maybe serialize the object? look into how it's done for query settings
            'players_setting': self.display_options.players,
            'device_setting': self.display_options.device,
            'max_level_setting': self.display_options.max_level,
            'resolved_monster_id': self.monster.monster_id,
            'query_settings': self.query_settings.serialize()
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        query_settings = QuerySettings.deserialize(ims['query_settings'])
        display_options = ButtonInfoToggles(ims['players_setting'], ims['device_setting'], ims['max_level_setting'])
        monster = dgcog.get_monster(ims['resolved_monster_id'])
        info = button_info.get_info(dgcog, monster)
        reaction_list = ims['reaction_list']
        return ButtonInfoViewState(original_author_id, menu_type, raw_query, user_config.color, display_options,
                                   monster, info, query_settings, reaction_list=reaction_list)

    def set_player_count(self, new_count):
        self.display_options.players = new_count

    def set_device(self, new_device):
        self.display_options.device = new_device

    def set_max_level(self, new_max_level):
        self.display_options.max_level = new_max_level


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
    def embed(state: ButtonInfoViewState):
        monster = state.monster
        info = state.info

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
            # EmbedField(
            #     'Common Buttons - {}'.format(get_max_level(monster)),
            #     Box(
            #         Text('*Inherits are assumed to be the max possible level (up to 110) and +297.*'),
            #         # janky, but python gives DeprecationWarnings when using \* in a regular string
            #         Text(r'*\* = on-color stat bonus applied*')
            #     )
            # ),
            # EmbedField(
            #     'Card Button Damage',
            #     BlockText(info.card_btn_str),
            #     inline=True
            # ),
            # EmbedField(
            #     'Team Button Contribution',
            #     BlockText(info.team_btn_str),
            #     inline=True
            # )
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
