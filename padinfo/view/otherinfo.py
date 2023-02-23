from typing import List

import prettytable
from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedField
from discordmenu.embed.text import LabeledText, Text
from redbot.core.utils.chat_formatting import box

from padinfo.view.components.evo_scroll_mixin import EvoScrollView
from padinfo.view.components.view_state_base_id import ViewStateBaseId, IdBaseView
from padinfo.view.links import LinksView


class OtherInfoViewState(ViewStateBaseId):
    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': OtherInfoView.VIEW_TYPE,
        })
        return ret


class OtherInfoView(IdBaseView, EvoScrollView):
    VIEW_TYPE = 'OtherInfo'

    @staticmethod
    def statsbox(m, plus: int):
        stat_cols = ['', 'HP', 'ATK', 'RCV']
        tbl = prettytable.PrettyTable(stat_cols)
        tbl.hrules = prettytable.NONE
        tbl.vrules = prettytable.NONE
        tbl.align = "l"
        levels = (1, m.level, 110, 120) if m.limit_mult > 0 else (m.level,)
        inh_tuple = (False, True) if plus == 297 else (False,)
        for lv in levels:
            for inh in inh_tuple:
                hp, atk, rcv, _ = m.stats(lv, plus=plus, inherit=inh)
                row_name = '(Inh)' if inh else 'Lv{}'.format(lv)
                if lv == 1 and inh:
                    continue  # Don't need to see inherits for Lv1
                tbl.add_row([row_name, hp, atk, rcv])
        return box(tbl.get_string())

    @classmethod
    def embed_fields(cls, state: OtherInfoViewState) -> List[EmbedField]:
        m = state.monster
        fields = [
            EmbedField(
                "Stats at +297:",
                Box(
                    # need to put these on the same line to get around discord's insane
                    # whitespace margins around code blocks
                    Text(cls.statsbox(m, plus=297)),
                    LabeledText("JP Name", m.name_ja),
                    LinksView.linksbox(m),
                    LabeledText("Added to DB", str(m.reg_date)) if m.reg_date else None,
                    LabeledText("Series", m.series.name_en),
                    Box(
                        LabeledText("Sell MP", '{:,}'.format(m.sell_mp)),
                        LabeledText("Buy MP", '{:,}'.format(m.buy_mp)) if m.buy_mp else None,
                        delimiter='  '),
                    Box(
                        LabeledText("Sell Gold", '{:,}'.format(m.sell_gold))
                    ),
                    Box(
                        LabeledText("`^expcurve`", '{:.1f}'.format(m.exp / 1000000).rstrip('0').rstrip('.') + 'M'
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
            cls.evos_embed_field(state)]
        return fields
