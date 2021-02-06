from typing import TYPE_CHECKING

import prettytable
from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from discordmenu.embed.text import LabeledText, LinkedText, Text
from redbot.core.utils.chat_formatting import box

from padinfo.common.external_links import puzzledragonx, youtube_search, skyozora, ilmina
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.links import LinksView
from padinfo.view_state.otherinfo import OtherInfoViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


def statsbox(m):
    stat_cols = ['', 'HP', 'ATK', 'RCV']
    tbl = prettytable.PrettyTable(stat_cols)
    tbl.hrules = prettytable.NONE
    tbl.vrules = prettytable.NONE
    tbl.align = "l"
    levels = (m.level, 110) if m.limit_mult > 0 else (m.level,)
    for lv in levels:
        for inh in (False, True):
            hp, atk, rcv, _ = m.stats(lv, plus=297, inherit=inh)
            row_name = '(Inh)' if inh else 'Lv{}'.format(lv)
            tbl.add_row([row_name, hp, atk, rcv])
    return box(tbl.get_string())


class OtherInfoView:
    @staticmethod
    def embed(state: OtherInfoViewState):
        m = state.monster
        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=puzzledragonx(m)),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=[
                EmbedField(
                    "Stats at +297:",
                    Box(
                        Text(statsbox(m)),
                        LabeledText("JP Name", m.name_ja),
                        LinksView.linksbox(m),
                        LabeledText("History", m.history_us) if m.history_us else None,
                        LabeledText("Series", m.series.name_en),
                        Box(
                            LabeledText("Sell MP", '{:,}'.format(m.sell_mp)),
                            LabeledText("Buy MP", '{:,}'.format(m.buy_mp)) if m.buy_mp else None,
                            delimiter='  '),
                        Box(
                            LabeledText("XP to Max", '{:.1f}'.format(m.exp / 1000000).rstrip('0').rstrip('.') + 'M'
                            if m.exp >= 1000000 else '{:,}'.format(m.exp)),
                            LabeledText("Max Level", str(m.level)),
                            delimiter='  '),
                        Box(
                            LabeledText("Weighted Stats", str(m.stats()[3])),
                            Text('LB {} (+{}%)'.format(m.stats(lv=110)[3], m.limit_mult)) if m.limit_mult > 0 else None,
                            delimiter=' | '),
                        LabeledText("Fodder EXP", '{:,}'.format(m.fodder_exp)),
                        Box(
                            LabeledText("Rarity", str(m.rarity)),
                            LabeledText("Cost", str(m.cost)),
                            delimiter=' ')))])
