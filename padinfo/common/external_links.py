import urllib.parse
from typing import TYPE_CHECKING

from tsutils.pad import get_pdx_id

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel

INFO_PDX_TEMPLATE = 'http://www.puzzledragonx.com/en/monster.asp?n={}'
YT_SEARCH_TEMPLATE = 'https://www.youtube.com/results?search_query={}'
SKYOZORA_TEMPLATE = 'http://pad.skyozora.com/pets/{}'
ILMINA_TEMPLATE = 'https://ilmina.com/#/CARD/{}'


def puzzledragonx(m: "MonsterModel"):
    return INFO_PDX_TEMPLATE.format(get_pdx_id(m))


def youtube_search(m: "MonsterModel"):
    return YT_SEARCH_TEMPLATE.format(urllib.parse.quote(m.name_ja))


def skyozora(m: "MonsterModel"):
    return SKYOZORA_TEMPLATE.format(m.monster_no_jp)


def ilmina(m: "MonsterModel"):
    return ILMINA_TEMPLATE.format(m.monster_no_jp)


def ilmina_skill(m: "MonsterModel"):
    return "https://ilmina.com/#/SKILL/{}".format(m.active_skill.active_skill_id) if m.active_skill else None
