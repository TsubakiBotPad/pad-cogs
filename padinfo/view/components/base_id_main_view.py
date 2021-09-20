from abc import abstractmethod
from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.text import Text, BoldText
from discordmenu.embed.view import EmbedView
from tsutils.enums import LsMultiplier

from padinfo.common.emoji_map import get_awakening_emoji, get_emoji
from padinfo.core.leader_skills import ls_multiplier_text, ls_single_multiplier_text
from padinfo.view.base import BaseIdView
from padinfo.view.components.view_state_base_id import ViewStateBaseId

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.models.awakening_model import AwakeningModel


def _get_awakening_text(awakening: "AwakeningModel"):
    return get_awakening_emoji(awakening.awoken_skill_id, awakening.name)


def _killer_latent_emoji(latent_name: str):
    return get_emoji('latent_killer_{}'.format(latent_name.lower()))


class BaseIdMainView(BaseIdView):
    transform_emojis = ['\N{DOWN-POINTING RED TRIANGLE}', get_emoji('downo'), get_emoji('downy'), get_emoji('downg'),
                        get_emoji('downb'), get_emoji('downp')]
    up_emoji = get_emoji('upgr')
    down_emoji = transform_emojis[0]

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
        if len(previous_transforms) == 0:
            active_cd = "({} -> {})".format(active_skill.turn_max, active_skill.turn_min) \
                if active_skill else 'None'
        else:
            skill_texts = []
            previous_transforms.reverse()
            for i, mon in enumerate(previous_transforms):
                skill = mon.active_skill
                # we can assume skill is not None because the monster transforms
                cooldown_text = '({}cd)'.format(str(skill.turn_max))
                if skill.turn_min != skill.turn_max:
                    cooldown_text = '{} -> {}'.format(skill.turn_min, skill.turn_max)
                skill_texts.append('{}{}'.format(cls.transform_emojis[i % len(cls.transform_emojis)], cooldown_text))
            skill_texts.append('{} ({} cd)'.format(cls.up_emoji, m.active_skill.turn_max))
            active_cd = ' '.join(skill_texts)
        return Box(
            BoldText('Active Skill'),
            BoldText(active_cd),
            delimiter=' '
        )

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
