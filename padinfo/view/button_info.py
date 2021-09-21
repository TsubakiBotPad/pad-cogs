from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedAuthor, EmbedField, EmbedMain
from discordmenu.embed.text import Text, BlockText
from discordmenu.embed.view import EmbedView
from tsutils.menu.footers import embed_footer_with_state
from tsutils.query_settings import QuerySettings

from padinfo.common.config import UserConfig
from padinfo.common.external_links import puzzledragonx
from padinfo.core.button_info import button_info, LIMIT_BREAK_LEVEL, SUPER_LIMIT_BREAK_LEVEL
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.components.view_state_base import ViewStateBase

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class ButtonInfoOptions:
    coop = 'Multiplayer'
    solo = 'Singleplayer'
    desktop = 'Desktop'
    mobile = 'Mobile'
    limit_break = 'Level 110'
    super_limit_break = 'Level 120'


class ButtonInfoToggles:
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
    async def deserialize(dbcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        query_settings = QuerySettings.deserialize(ims['query_settings'])
        display_options = ButtonInfoToggles(ims['players_setting'], ims['device_setting'], ims['max_level_setting'])
        monster = dbcog.get_monster(ims['resolved_monster_id'])
        info = button_info.get_info(dbcog, monster)
        reaction_list = ims['reaction_list']
        return ButtonInfoViewState(original_author_id, menu_type, raw_query, user_config.color, display_options,
                                   monster, info, query_settings, reaction_list=reaction_list)

    def set_player_count(self, new_count):
        self.display_options.players = new_count

    def set_device(self, new_device):
        self.display_options.device = new_device

    def set_max_level(self, new_max_level):
        self.display_options.max_level = new_max_level


def get_stat_block(main, sub, total):
    return BlockText(
        Box(
            Text('Base:    {}'.format(int(round(main)))),
            Text('Subattr: {}'.format(int(round(sub)))),
            Text('Total:   {}'.format(int(round(total))))
        )
    )


def get_max_stats_without_latents(info, is_coop):
    main = info.main if is_coop else info.main_solo
    sub = info.sub if is_coop else info.sub_solo
    total = info.total if is_coop else info.total_solo
    return get_stat_block(main, sub, total)


def get_120_stats_without_latents(info, is_coop):
    main = info.main_slb if is_coop else info.main_solo_slb
    sub = info.sub_slb if is_coop else info.sub_solo_slb
    total = info.total_slb if is_coop else info.total_solo_slb
    return get_stat_block(main, sub, total)


def get_max_stats_with_latents(info, is_coop):
    main = info.main_latent if is_coop else info.main_solo_latent
    sub = info.sub_latent if is_coop else info.sub_solo_latent
    total = info.total_latent if is_coop else info.total_solo_latent
    return get_stat_block(main, sub, total)


def get_120_stats_with_latents(info, is_coop):
    main = info.main_slb_latent if is_coop else info.main_solo_slb_latent
    sub = info.sub_slb_latent if is_coop else info.sub_solo_slb_latent
    total = info.total_slb_latent if is_coop else info.total_solo_slb_latent
    return get_stat_block(main, sub, total)


def get_mobile_btn_str(btn_str):
    output = []
    lines = btn_str.split('\n')
    for line in lines:
        partition = line.find('(')
        name = line[:partition].strip()
        damage = line[partition:]
        output.append('{}\n   {}'.format(name, damage))
    return '\n'.join(output)


class ButtonInfoView:
    VIEW_TYPE = 'ButtonInfo'

    @staticmethod
    def get_max_level_text(monster, is_max_110):
        limit = str(LIMIT_BREAK_LEVEL) if is_max_110 else str(SUPER_LIMIT_BREAK_LEVEL)
        level_text = limit if monster.limit_mult != 0 else 'Max ({})'.format(monster.level)
        return 'Lv. {}'.format(level_text)

    @staticmethod
    def get_common_buttons_title_text(monster, is_max_110):
        return 'Common Buttons - Base Card {} {}'.format(
            ButtonInfoView.get_max_level_text(monster, is_max_110),
            '(Atk+ Latents)' if is_max_110 or monster.limit_mult == 0 else '(Atk++ Latents)'
        )

    @staticmethod
    def embed(state: ButtonInfoViewState):
        is_coop = state.display_options.players == ButtonInfoOptions.coop
        is_desktop = state.display_options.device == ButtonInfoOptions.desktop
        max_110 = state.display_options.max_level == ButtonInfoOptions.limit_break
        monster = state.monster
        info = state.info

        fields = [
            EmbedField(
                # this block does not change if the lv110/lv120 toggle is clicked
                ButtonInfoView.get_max_level_text(monster, True),
                Box(
                    Text('Without Latents'),
                    # avoid whitespace after code block
                    Box(
                        get_max_stats_without_latents(info, is_coop),
                        Text('With Latents (Atk+)'),
                        delimiter=''
                    ),
                    get_max_stats_with_latents(info, is_coop)
                ),
                inline=True
            ),
            EmbedField(
                'Lv. 120',
                Box(
                    Text('Without Latents'),
                    # avoid whitespace after code block
                    Box(
                        get_120_stats_without_latents(info, is_coop),
                        Text('With Latents (Atk++)'),
                        delimiter=''
                    ),
                    get_120_stats_with_latents(info, is_coop)
                ),
                inline=True
            ) if monster.limit_mult != 0 else None,
            EmbedField(
                ButtonInfoView.get_common_buttons_title_text(monster, max_110),
                Box(
                    Text('*Inherits are assumed to be the max possible level (up to 110) and +297.*'),
                    # janky, but python gives DeprecationWarnings when using \* in a regular string
                    Text(r'*\* = on-color stat bonus applied*'),
                    Text('Card Button Damage'),
                    # done this way to not have the whitespace after code block
                    Box(
                        BlockText(info.get_card_btn_str(is_coop, max_110)),
                        Text('Team Button Contribution'),
                        delimiter=''
                    ),
                    BlockText(info.get_team_btn_str(is_coop, max_110))
                )
            ) if is_desktop else None,
            EmbedField(
                ButtonInfoView.get_common_buttons_title_text(monster, max_110),
                Box(
                    Text('*Inherits are assumed to be the max possible level (up to 110) and +297.*'),
                    # janky, but python gives DeprecationWarnings when using \* in a regular string
                    Text(r'*\* = on-color stat bonus applied*')
                )
            ) if not is_desktop else None,
            EmbedField(
                'Card Button Damage',
                BlockText(get_mobile_btn_str(info.get_card_btn_str(is_coop, max_110))),
                inline=True
            ) if not is_desktop else None,
            EmbedField(
                'Team Button Contribution',
                BlockText(get_mobile_btn_str(info.get_team_btn_str(is_coop, max_110))),
                inline=True
            ) if not is_desktop else None
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                description='(Co-op mode)' if is_coop else '(Singleplayer mode)'
            ),
            embed_author=EmbedAuthor(
                MonsterHeader.long_v2(monster).to_markdown(),
                puzzledragonx(monster),
                MonsterImage.icon(monster)
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
