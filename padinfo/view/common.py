from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.text import Text, BoldText
from tsutils import char_to_emoji
from tsutils.enums import LsMultiplier
from tsutils.query_settings import QuerySettings

from padinfo.common.emoji_map import get_awakening_emoji, get_emoji
from padinfo.core.leader_skills import ls_multiplier_text, ls_single_multiplier_text
from padinfo.view.components.monster.header import MonsterHeader

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.models.awakening_model import AwokenSkillModel


async def get_monster_from_ims(dbcog, ims: dict):
    query = ims.get('query') or ims['raw_query']
    query_settings = QuerySettings.deserialize(ims.get('query_settings'))

    resolved_monster_id_str = ims.get('resolved_monster_id')
    resolved_monster_id = int(resolved_monster_id_str or 0)
    if resolved_monster_id:
        return dbcog.database.graph.get_monster(resolved_monster_id, server=query_settings.server)
    monster = await dbcog.find_monster(query, ims['original_author_id'])
    return monster


def get_awoken_skill_description(awoken_skill: "AwokenSkillModel"):
    emoji_text = get_awakening_emoji(awoken_skill.awoken_skill_id, awoken_skill.name)
    desc = awoken_skill.desc_en
    return Box(
        Text(emoji_text),
        BoldText(awoken_skill.name_en),
        Text(desc),
        delimiter=' '
    )


def invalid_monster_text(query: str, monster: "MonsterModel", append_text: str, link=False):
    base_text = 'Your query `{}` found {}{}.'
    return base_text.format(query, MonsterHeader.short_with_emoji(monster, link=link).to_markdown(), append_text)


def leader_skill_header(m: "MonsterModel", lsmultiplier: LsMultiplier, transform_base: "MonsterModel"):
    return Box(
        BoldText('Leader Skill'),
        BoldText(ls_multiplier_text(m.leader_skill) if lsmultiplier == LsMultiplier.lsdouble
                 else get_emoji('1x') + ' ' + ls_single_multiplier_text(m.leader_skill)),
        BoldText('(' + get_emoji(
            '\N{DOWN-POINTING RED TRIANGLE}') + '7x6)') if m != transform_base and transform_base.leader_skill.is_7x6 else None,
        delimiter=' '
    )
