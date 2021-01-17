from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.menu import EmbedView
from discordmenu.embed.text import Text, BoldText, LabeledText, HighlightableLinks, LinkedText

from padinfo.common.emoji_map import get_emoji, format_emoji, AWAKENING_ID_TO_EMOJI_NAME_MAP, emoji_markdown
from padinfo.common.padx import monster_url
from padinfo.leader_skills import createMultiplierText
from padinfo.view.components.base import pad_info_footer
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel
    from dadguide.models.awakening_model import AwakeningModel


def _get_awakening_text(awakening: "AwakeningModel"):
    return format_emoji(get_emoji(
        AWAKENING_ID_TO_EMOJI_NAME_MAP.get(awakening.awoken_skill_id, awakening.name)))


def _killer_latent_emoji(latent_name: str):
    return emoji_markdown('latent_killer_{}'.format(latent_name.lower()))


def _get_awakening_emoji_for_stats(m: "MonsterModel", i: int):
    return emoji_markdown(i) if m.awakening_count(i) and not m.is_equip else ''


def _get_stat_text(stat, lb_stat, icon):
    return Box(
        Text(str(stat)),
        Text("({})".format(lb_stat)) if lb_stat else None,
        Text(icon) if icon else None,
        delimiter=' '
    )


def _monster_is_enhance(m: "MonsterModel"):
    return any(x if x.name == 'Enhance' else None for x in m.types)


class IdView:
    @staticmethod
    def awakenings_row(m: "MonsterModel"):
        if len(m.awakenings) == 0:
            return Box(Text('No Awakenings'))

        normal_awakenings = len(m.awakenings) - m.superawakening_count
        normal_awakenings_emojis = [_get_awakening_text(a) for a in m.awakenings[:normal_awakenings]]
        super_awakenings_emojis = [_get_awakening_text(a) for a in m.awakenings[normal_awakenings:]]

        return Box(
            Box(*[Text(e) for e in normal_awakenings_emojis], delimiter=' '),
            Box(
                Text(emoji_markdown('sa_questionmark')),
                *[Text(e) for e in super_awakenings_emojis],
                delimiter=' ')
        )

    @staticmethod
    def killers_row(m: "MonsterModel", is_transform_base):
        killers_text = 'Any' if 'Any' in m.killers else ' '.join([_killer_latent_emoji(k) for k in m.killers])
        available_killer_text = 'Available killers:' if is_transform_base else 'Avail. killers (pre-xform):'
        return Box(
            BoldText(available_killer_text),
            Text('[{} slots]'.format(m.latent_slots)),
            Text(killers_text),
            delimiter=' '
        )

    @staticmethod
    def misc_info(m: "MonsterModel", true_evo_type_raw: str, acquire_raw: str, base_rarity: str):
        rarity = Box(
            LabeledText('Rarity', str(m.rarity)),
            Text('({})'.format(LabeledText('Base', str(base_rarity)).to_markdown())),
            Text("" if m.orb_skin_id is None else "(Orb Skin)"),
            delimiter=' '
        )

        cost = LabeledText('Cost', str(m.cost))
        acquire = BoldText(acquire_raw) if acquire_raw else None
        valid_true_evo_types = ("Reincarnated", "Assist", "Pixel", "Super Reincarnated")
        true_evo_type = BoldText(true_evo_type_raw) if true_evo_type_raw in valid_true_evo_types else None

        return Box(rarity, cost, acquire, true_evo_type)

    @staticmethod
    def stats(m: "MonsterModel"):
        hp, atk, rcv, weighted = m.stats()
        lb_hp, lb_atk, lb_rcv, lb_weighted = m.stats(lv=110) if m.limit_mult > 0 else (None, None, None, None)
        return Box(
            LabeledText('HP', _get_stat_text(hp, lb_hp, _get_awakening_emoji_for_stats(m, 1))),
            LabeledText('ATK', _get_stat_text(atk, lb_atk, _get_awakening_emoji_for_stats(m, 2))),
            LabeledText('RCV', _get_stat_text(rcv, lb_rcv, _get_awakening_emoji_for_stats(m, 3))),
            LabeledText('Fodder EXP', "{:,}".format(m.fodder_exp)) if _monster_is_enhance(m) else None
        )

    @staticmethod
    def stats_header(m: "MonsterModel"):
        voice = emoji_markdown(63) if m.awakening_count(63) and not m.is_equip else ''
        header = Box(
            Text(voice),
            Text('Stats'),
            Text('(LB, +{}%)'.format(m.limit_mult)) if m.limit_mult else None,
            delimiter=' '
        )
        return header

    @staticmethod
    def active_skill_header(m: "MonsterModel"):
        active_skill = m.active_skill
        active_cd = "({} -> {})".format(active_skill.turn_max, active_skill.turn_min) if active_skill else 'None'
        return Box(
            BoldText('Active Skill'),
            BoldText(active_cd),
            delimiter=' '
        )

    @staticmethod
    def leader_skill_header(m: "MonsterModel"):
        return Box(
            BoldText('Leader Skill'),
            BoldText(createMultiplierText(m.leader_skill)),
            delimiter=' '
        )

    @staticmethod
    def embed(m: "MonsterModel", color, is_transform_base, true_evo_type_raw, acquire_raw, base_rarity,
              alt_monsters: List["MonsterModel"]):
        fields = [
            EmbedField(
                '/'.join(['{}'.format(t.name) for t in m.types]),
                Box(
                    IdView.awakenings_row(m),
                    IdView.killers_row(m, is_transform_base)
                )
            ),
            EmbedField(
                'Inheritable' if m.is_inheritable else 'Not inheritable',
                IdView.misc_info(m, true_evo_type_raw, acquire_raw, base_rarity),
                inline=True
            ),
            EmbedField(
                IdView.stats_header(m).to_markdown(),
                IdView.stats(m),
                inline=True
            ),
            EmbedField(
                IdView.active_skill_header(m).to_markdown(),
                Text(m.active_skill.desc if m.active_skill else 'None')
            ),
            EmbedField(
                IdView.leader_skill_header(m).to_markdown(),
                Text(m.leader_skill.desc if m.leader_skill else 'None')
            ),
            EmbedField(
                "Alternate Evos",
                HighlightableLinks(
                    links=[LinkedText(str(m.monster_id), monster_url(m)) for m in alt_monsters],
                    highlighted=next(i for i, mon in enumerate(alt_monsters) if m.monster_id == mon.monster_id)
                )
            )
        ]

        return EmbedView(
            EmbedMain(
                color=color,
                title=MonsterHeader.long_v2(m).to_markdown(),
                url=monster_url(m)),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m)),
            embed_footer=pad_info_footer(),
            embed_fields=fields)
