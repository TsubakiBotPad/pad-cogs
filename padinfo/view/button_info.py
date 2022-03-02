from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedAuthor, EmbedField, EmbedMain
from discordmenu.embed.text import Text, BlockText
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.view_state_base import ViewStateBase
from tsutils.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.core.button_info import button_info, LIMIT_BREAK_LEVEL, SUPER_LIMIT_BREAK_LEVEL, ButtonInfoStatSet, \
    ButtonInfoResult
from padinfo.view.components.evo_scroll_mixin import EvoScrollView, EvoScrollViewState, MonsterEvolution

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


class ButtonInfoViewState(ViewStateBase, EvoScrollViewState):
    def __init__(self, original_author_id, menu_type, raw_query, color, display_options: ButtonInfoToggles,
                 monster: "MonsterModel", alt_monsters: List[MonsterEvolution],
                 info: ButtonInfoResult, query_settings: QuerySettings,
                 reaction_list: List[str] = None):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None, reaction_list=reaction_list)
        self.color = color
        self.display_options = display_options
        self.monster = monster
        self.info = info
        self.query_settings = query_settings

        self.alt_monsters = alt_monsters
        self.alt_monster_ids = [m.monster.monster_id for m in self.alt_monsters]

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

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        query_settings = QuerySettings.deserialize(ims['query_settings'])
        display_options = ButtonInfoToggles(ims['players_setting'], ims['device_setting'], ims['max_level_setting'])
        monster = dbcog.get_monster(int(ims['resolved_monster_id']))
        alt_monsters = cls.get_alt_monsters_and_evos(dbcog, monster)
        info = button_info.get_info(dbcog, monster)
        reaction_list = ims['reaction_list']
        return ButtonInfoViewState(original_author_id, menu_type, raw_query, user_config.color, display_options,
                                   monster, alt_monsters, info, query_settings, reaction_list=reaction_list)

    def set_player_count(self, new_count):
        self.display_options.players = new_count

    def set_device(self, new_device):
        self.display_options.device = new_device

    def set_max_level(self, new_max_level):
        self.display_options.max_level = new_max_level


def get_stat_block(bi_stat_set: ButtonInfoStatSet):
    return BlockText(
        Box(
            Text('Base:    {}'.format(int(round(bi_stat_set.main)))),
            Text('Subattr: {}'.format(int(round(bi_stat_set.sub)))),
            Text('Total:   {}'.format(int(round(bi_stat_set.total))))
        )
    )


def get_mobile_btn_str(btn_str):
    output = []
    lines = btn_str.split('\n')
    for line in lines:
        partition = line.find('(')
        name = line[:partition].strip()
        damage = line[partition:]
        output.append('{}\n   {}'.format(name, damage))
    return '\n'.join(output)


class ButtonInfoView(EvoScrollView):
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

    @classmethod
    def embed(cls, state: ButtonInfoViewState):
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
                        get_stat_block(info.coop if is_coop else info.solo),
                        Text('With Latents (Atk+)'),
                        delimiter=''
                    ),
                    get_stat_block(info.coop_latent if is_coop else info.solo_latent)
                ),
                inline=True
            ),
            EmbedField(
                'Lv. 120',
                Box(
                    Text('Without Latents'),
                    # avoid whitespace after code block
                    Box(
                        get_stat_block(info.coop_slb if is_coop else info.solo_slb),
                        Text('With Latents (Atk++)'),
                        delimiter=''
                    ),
                    get_stat_block(info.coop_slb_latent if is_coop else info.solo_slb_latent)
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
            ) if not is_desktop else None,
            cls.evos_embed_field(state)
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                description='(Co-op mode)' if is_coop else '(Singleplayer mode)'
            ),
            embed_author=EmbedAuthor(
                MonsterHeader.menu_title(monster).to_markdown(),
                MonsterLink.header_link(monster, state.query_settings),
                MonsterImage.icon(monster.monster_id)
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
