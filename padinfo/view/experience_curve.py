from math import ceil
from typing import TYPE_CHECKING, Text, Union

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedField, EmbedMain, EmbedThumbnail
from discordmenu.embed.text import LabeledText
from discordmenu.embed.view import EmbedView
from discordmenu.emoji.emoji_cache import emoji_cache
from redbot.core.utils.chat_formatting import humanize_number
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel

SSG_EXP = 4_000_000
GLOBE_EXP = {
    0: 2_600_000,
    1: 2_900_000,
    2: 3_250_000,
    3: 3_000_000,
    4: 3_000_000,
}
TA2_EXP = 12_000_000
TA3_EXP = 50_000_000


class ExperienceCurveViewProps:
    def __init__(self, monster: "MonsterModel", low: int, high: int, offset: Union[float, int]):
        self.monster = monster
        self.low = low
        self.high = high

        if offset <= 1:
            if low <= 99:
                self.offset = int((monster.exp_to_level(low + 1) - monster.exp_to_level(low)) * offset)
            elif low <= 110:
                self.offset = int(5e6 * offset)
            else:
                self.offset = int(20e6 * offset)
        else:
            self.offset = offset


def get_normal_exp_difference(monster: "MonsterModel", low: int, high: int, offset: int) -> int:
    if low >= 99:
        return 0
    total_low = monster.exp_to_level(low)
    total_high = monster.exp_to_level(min(high, 99))
    total = int(total_high - total_low)
    if low < 99:
        return total - offset
    return total


def get_lb_exp_difference(monster: "MonsterModel", low: int, high: int, offset: int) -> int:
    if high <= 99 or low >= 110:
        return 0
    total = int(5e6 * (min(high, 110) - max(low, 100)))
    if 99 <= low < 110:
        return total - offset
    return total


def get_slb_exp_difference(monster: "MonsterModel", low: int, high: int, offset: int) -> int:
    if high <= 110:
        return 0
    total = int(20e6 * (high - max(low, 110)))
    if 110 <= low < 120:
        return total - offset
    return total


def trunc_humanize(n: int) -> str:
    def strip_float(f) -> str:
        return str(float(f)).rstrip('0').rstrip('.')

    if n < 1e6:
        return strip_float(round(n, 1))
    if n < 1e9:
        return strip_float(round(n / 1e6, 1)) + 'm'
    if n < 1e12:
        return strip_float(round(n / 1e9, 1)) + 'b'
    return str(n)


def get_total_needed(monster: "MonsterModel", low: int, high: int, offset: int, amount: int, is_light: bool) -> int:
    ssg = SSG_EXP
    if is_light:
        ssg *= 1.5

    total = ceil(get_normal_exp_difference(monster, low, high, offset) / amount)

    lb = get_lb_exp_difference(monster, low, high, offset)
    if low <= 99:
        lb -= ssg
    total += ceil(max(0, lb) / amount)

    slb = get_slb_exp_difference(monster, low, high, offset)
    if low <= 110:
        slb -= ssg * 5
    total += ceil(max(0, slb) / amount)

    return int(total)


class ExperienceCurveView:
    VIEW_TYPE = 'ExperienceCurve'

    @staticmethod
    def embed(state, props: ExperienceCurveViewProps):
        regular = get_normal_exp_difference(props.monster, props.low, props.high, props.offset)
        lb = get_lb_exp_difference(props.monster, props.low, props.high, props.offset)
        slb = get_slb_exp_difference(props.monster, props.low, props.high, props.offset)
        is_light = props.monster.full_damage_attr.value == 3
        return EmbedView(
            EmbedMain(
                color=state.query_settings.embedcolor,
                title=MonsterHeader.menu_title(props.monster, use_emoji=True),
                url=MonsterLink.header_link(props.monster, query_settings=state.query_settings),
                description=Text(f'lv{props.low} -> lv{props.high} ('
                                 + (trunc_humanize(props.monster.exp_curve) if props.monster.exp_curve else "no")
                                 + f' curve)'),
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(props.monster.monster_id)),
            embed_fields=[
                EmbedField(
                    title='Exact',
                    body=Box(
                        LabeledText("Reg", humanize_number(regular)),
                        LabeledText("LB", humanize_number(lb)),
                        LabeledText("SLB", humanize_number(slb)),
                        LabeledText("Net", humanize_number(regular + lb + slb))
                    ),
                    inline=True
                ),
                EmbedField(
                    title='Approx',
                    body=Box(
                        LabeledText("Reg", trunc_humanize(regular)),
                        LabeledText("LB", trunc_humanize(lb)),
                        LabeledText("SLB", trunc_humanize(slb)),
                        LabeledText("Net", trunc_humanize(regular + lb + slb))
                    ),
                    inline=True
                ),
                EmbedField(
                    title='Resources',
                    body=Box(
                        LabeledText("Globes " +
                                    emoji_cache.get_emoji(f'orb_{props.monster.full_damage_attr.name.lower()}'),
                                    str(get_total_needed(props.monster, props.low, props.high, props.offset,
                                                         ceil(1.5 * GLOBE_EXP[props.monster.full_damage_attr.value]),
                                                         is_light))),
                        LabeledText("TA2", str(get_total_needed(props.monster, props.low, props.high, props.offset,
                                                                TA2_EXP, is_light))),
                        LabeledText("TA3", str(get_total_needed(props.monster, props.low, props.high, props.offset,
                                                                TA3_EXP, is_light))),
                    ),
                    inline=True
                )
            ],
            embed_footer=embed_footer_with_state(state, qs=state.query_settings))
