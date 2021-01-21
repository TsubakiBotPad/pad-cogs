from typing import TYPE_CHECKING

from padinfo.common.emoji_map import get_emoji

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class MonsterEmoji:
    @staticmethod
    def attribute(monster: "MonsterModel"):
        attr1 = monster.attr1.name.lower()
        attr2 = monster.attr2.name.lower()
        emoji = "{}_{}".format(attr1, attr2) if attr1 != attr2 else 'orb_{}'.format(attr1)
        return get_emoji(emoji)
