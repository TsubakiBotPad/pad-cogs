from typing import TYPE_CHECKING, Any, Union

from discordmenu.embed.base import Box
from discordmenu.embed.text import BoldText, Text
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.custom_emoji import get_awakening_emoji
from tsutils.tsubaki.monster_header import MonsterHeader

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.models.awakening_model import AwokenSkillModel


async def get_monster_from_ims(dbcog, ims: dict):
    query = ims.get('query') or ims['raw_query']
    qs = QuerySettings.deserialize(ims.get('qs'))

    resolved_monster_id_str = ims.get('resolved_monster_id')
    resolved_monster_id = int(resolved_monster_id_str or 0)
    if resolved_monster_id:
        return dbcog.database.graph.get_monster(resolved_monster_id, server=qs.server)
    monster = await dbcog.find_monster(query, ims['original_author_id'])
    return monster


def get_awoken_skill_description(awoken_skill: "AwokenSkillModel", show_help: Union[bool, Any] = False, token_map: dict = None):
    if token_map is None:
        token_map = {}
    emoji_text = get_awakening_emoji(awoken_skill.awoken_skill_id, awoken_skill.name)
    if not show_help:
        desc = awoken_skill.desc_en
    else:
        if awoken_skill.awoken_skill_id not in token_map:
            desc = "No modifiers found. Please contact Tsubaki admins for support."
        else:
            tokens = token_map[awoken_skill.awoken_skill_id]
            tokens: set
            desc = ', '.join('`{}`'.format(token) for token in list(tokens))
    return Box(
        Text(emoji_text),
        BoldText(awoken_skill.name_en),
        Text(desc),
        delimiter=' '
    )


def invalid_monster_text(query: str, monster: "MonsterModel", append_text: str):
    monster_name = MonsterHeader.text_with_emoji(monster)
    return f'Your query `{query}` found {monster_name}{append_text}.'
