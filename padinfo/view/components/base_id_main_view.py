from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TYPE_CHECKING

import jinja2
from discordmenu.embed.base import Box
from discordmenu.embed.text import BoldText, Text
from discordmenu.embed.view import EmbedView
from discordmenu.emoji.emoji_cache import emoji_cache
from tsutils.tsubaki import number_emoji_small
from tsutils.enums import LsMultiplier

from padinfo.common.emoji_map import get_awakening_emoji, get_emoji
from padinfo.core.leader_skills import ls_multiplier_text, ls_single_multiplier_text
from padinfo.view.base import BaseIdView
from padinfo.view.components.view_state_base_id import ViewStateBaseId

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.models.active_skill_model import ActiveSkillModel
    from dbcog.models.awakening_model import AwakeningModel
    from dbcog.models.awoken_skill_model import AwokenSkillModel


def _get_awakening_text(awakening: "AwakeningModel"):
    return get_awakening_emoji(awakening.awoken_skill_id, awakening.name)


def _killer_latent_emoji(latent_name: str):
    return get_emoji('latent_killer_{}'.format(latent_name.lower()))


def _make_prefix(idx, compound_skill_type_id):
    return {
        0: '',
        1: emoji_cache.get_emoji('bd') + ' ',
        2: number_emoji_small(idx) + ' ',
        3: number_emoji_small(idx) + ' '
    }.get(compound_skill_type_id)


class BaseIdMainView(BaseIdView, ABC):
    transform_emoji_names = ['downr', 'downo', 'downy', 'downg', 'downb', 'downp']
    up_emoji_name = 'upgr'
    down_emoji_name = transform_emoji_names[0]

    active_skill_type_texts = {
        0: None,
        1: f"[\N{GAME DIE} Random]",
        2: f"[\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16} Transforms]",
        3: f"[\N{BLACK UNIVERSAL RECYCLING SYMBOL}\N{VARIATION SELECTOR-16} Cycles]"
    }

    @staticmethod
    def normal_awakenings_row(m: "MonsterModel"):
        normal_awakenings = len(m.awakenings) - m.superawakening_count
        normal_awakenings_emojis = [_get_awakening_text(a) for a in m.awakenings[:normal_awakenings]]
        return Box(*[Text(e) for e in normal_awakenings_emojis], delimiter=' ')

    @staticmethod
    def super_awakenings_row(m: "MonsterModel"):
        normal_awakenings = len(m.awakenings) - m.superawakening_count
        super_awakenings_emojis = [_get_awakening_text(a) for a in m.awakenings[normal_awakenings:]]
        return Box(
            Text(get_emoji('sa_questionmark')),
            *[Text(e) for e in super_awakenings_emojis],
            delimiter=' ') if len(super_awakenings_emojis) > 0 else None

    @staticmethod
    def killers_row(m: "MonsterModel", transform_base):
        killers = m.killers if m == transform_base else transform_base.killers
        killers_text = 'Any' if 'Any' in killers else \
            ' '.join(_killer_latent_emoji(k) for k in killers)
        return Box(
            BoldText('Available killers:'),
            Text('\N{DOWN-POINTING RED TRIANGLE}' if m != transform_base else ''),
            Text('[{} slots]'.format(m.latent_slots if m == transform_base
                                     else transform_base.latent_slots)),
            Text(killers_text),
            delimiter=' '
        )

    @classmethod
    def active_skill_header(cls, m: "MonsterModel", previous_transforms: List["MonsterModel"]):

        active_skill = m.active_skill
        if active_skill is None:
            return BoldText('Active Skill')

        if len(previous_transforms) == 0:
            active_cd = "({} -> {})".format(active_skill.turn_max, active_skill.turn_min)
        else:
            skill_texts = []
            previous_transforms.reverse()
            for i, mon in enumerate(previous_transforms):
                skill = mon.active_skill
                # we can assume skill is not None because the monster transforms
                cooldown_text = '({}cd)'.format(str(skill.turn_max))
                if skill.turn_min != skill.turn_max:
                    cooldown_text = '{} -> {}'.format(skill.turn_min, skill.turn_max)
                skill_texts.append(
                    '{}{}'.format(get_emoji(cls.transform_emoji_names[i % len(cls.transform_emoji_names)]),
                                  cooldown_text))
            skill_texts.append('{} ({} cd)'.format(get_emoji(cls.up_emoji_name), m.active_skill.turn_max))
            active_cd = ' '.join(skill_texts)

        return Box(
            BoldText('Active Skill'),
            cls.get_compound_active_text(active_skill),
            BoldText(active_cd),
            delimiter=' '
        )

    @classmethod
    def get_compound_active_text(cls, active: Optional["ActiveSkillModel"]) -> Optional[Box]:
        text = cls.active_skill_type_texts.get(active.compound_skill_type_id)
        if text is None:
            return None
        return BoldText(text)

    @classmethod
    def active_skill_text(cls, active_skill: Optional["ActiveSkillModel"],
                          awoken_skill_map: Dict[int, "AwokenSkillModel"]):
        jinja2_replacements = {
            'awoskills': {f"id{awid}": f"{get_awakening_emoji(awid)} {awo.name_en}"
                          for awid, awo in awoken_skill_map.items()}
        }

        if active_skill is None:
            return 'None'
        return "\n".join(_make_prefix(c, active_skill.compound_skill_type_id)
                         + jinja2.Template(subskill.desc_templated).render(**jinja2_replacements)
                         for c, subskill in enumerate(active_skill.active_subskills, 1))

    @staticmethod
    def leader_skill_header(m: "MonsterModel", lsmultiplier: LsMultiplier, transform_base: "MonsterModel"):
        return Box(
            BoldText('Leader Skill'),
            BoldText(ls_multiplier_text(m.leader_skill) if lsmultiplier == LsMultiplier.lsdouble
                     else get_emoji('1x') + ' ' + ls_single_multiplier_text(m.leader_skill)),
            BoldText('(' + get_emoji(
                '\N{DOWN-POINTING RED TRIANGLE}') + '7x6)') if m != transform_base and transform_base.leader_skill.is_7x6 else None,
            delimiter=' '
        )

    @classmethod
    @abstractmethod
    def embed(cls, state: ViewStateBaseId) -> EmbedView:
        ...
