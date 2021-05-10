from typing import TYPE_CHECKING

import prettytable
from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.text import LabeledText, Text
from discordmenu.embed.view import EmbedView
from redbot.core.utils.chat_formatting import box
from tsutils import embed_footer_with_state

from padinfo.common.external_links import puzzledragonx
from padinfo.view.base import BaseIdView
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.view_state_base_id import ViewStateBaseId
from padinfo.view.id import evos_embed_field
from padinfo.view.links import LinksView

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class OtherInfoViewState(ViewStateBaseId):
    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': OtherInfoView.VIEW_TYPE,
        })
        return ret


def statsbox(m):
    stat_cols = ['', 'HP', 'ATK', 'RCV']
    tbl = prettytable.PrettyTable(stat_cols)
    tbl.hrules = prettytable.NONE
    tbl.vrules = prettytable.NONE
    tbl.align = "l"
    levels = (m.level, 110, 120) if m.limit_mult > 0 else (m.level,)
    for lv in levels:
        for inh in (False, True):
            hp, atk, rcv, _ = m.stats(lv, plus=297, inherit=inh)
            row_name = '(Inh)' if inh else 'Lv{}'.format(lv)
            tbl.add_row([row_name, hp, atk, rcv])
    return box(tbl.get_string())


class OtherInfoView(BaseIdView):
    VIEW_TYPE = 'OtherInfo'

    @classmethod
    def embed(cls, state: OtherInfoViewState):
        m: "MonsterModel" = state.monster
        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_maybe_tsubaki(state.monster,
                                                       state.alt_monsters[0].monster.monster_id == cls.TSUBAKI
                                                       ).to_markdown(),
                url=puzzledragonx(m)),
            embed_footer=embed_footer_with_state(state),
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
                            delimiter=' '))),
                evos_embed_field(state)])
