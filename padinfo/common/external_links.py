from typing import TYPE_CHECKING

import tsutils

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

INFO_PDX_TEMPLATE = 'http://www.puzzledragonx.com/en/monster.asp?n={}'


def monster_url(m: "MonsterModel"):
    return INFO_PDX_TEMPLATE.format(tsutils.get_pdx_id(m))
