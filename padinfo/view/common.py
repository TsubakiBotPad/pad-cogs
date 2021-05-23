from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.text import Text, BoldText

from padinfo.common.emoji_map import get_awakening_emoji

if TYPE_CHECKING:
    from dadguide.models.awakening_model import AwokenSkillModel


async def get_monster_from_ims(dgcog, ims: dict):
    query = ims.get('query') or ims['raw_query']

    resolved_monster_id_str = ims.get('resolved_monster_id')
    resolved_monster_id = int(resolved_monster_id_str) if resolved_monster_id_str else None
    if resolved_monster_id:
        return dgcog.database.graph.get_monster(resolved_monster_id)
    monster = await dgcog.find_monster(query, ims['original_author_id'])
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
