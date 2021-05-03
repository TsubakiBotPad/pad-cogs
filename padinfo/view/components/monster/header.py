from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.text import LinkedText, Text

from padinfo.common.emoji_map import get_attribute_emoji_by_monster
from padinfo.common.external_links import puzzledragonx

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class MonsterHeader:
    @staticmethod
    def jp_suffix(m: "MonsterModel", subname_on_override=True):
        suffix = ""
        if m.roma_subname and (subname_on_override or m.name_en_override is None):
            suffix += ' [{}]'.format(m.roma_subname)
        if not m.on_na:
            suffix += ' (JP only)'
        return suffix

    @staticmethod
    def short(m: "MonsterModel", link=False):
        type_emojis = ''
        msg = '[{}] {}{}'.format(m.monster_no_na, type_emojis, m.name_en)
        return '[{}]({})'.format(msg, puzzledragonx(m)) if link else msg

    @staticmethod
    def long(m: "MonsterModel", link=False):
        msg = MonsterHeader.short(m) + MonsterHeader.jp_suffix(m)
        return '[{}]({})'.format(msg, puzzledragonx(m)) if link else msg

    @staticmethod
    def name(m: "MonsterModel", link=False, show_jp=False):
        msg = '[{}] {}{}'.format(
            m.monster_no_na,
            m.name_en,
            MonsterHeader.jp_suffix(m) if show_jp else '')
        return LinkedText(msg, puzzledragonx(m)) if link else Text(msg)

    @staticmethod
    def long_v2(m: "MonsterModel", link=False):
        msg = '[{}] {}{}'.format(m.monster_no_na, m.name_en, MonsterHeader.jp_suffix(m))
        return LinkedText(msg, puzzledragonx(m)) if link else Text(msg)

    @staticmethod
    def long_maybe_tsubaki(m: "MonsterModel", is_tsubaki):
        """Returns long_v2 as well as an `!` if the monster is Tsubaki
    
        To celebrate 1000 issues/PRs in our main Tsubaki repo, we added this easter egg! Yay!
        """
        return Text('[{}] {}{}{}'.format(
            m.monster_no_na,
            m.name_en,
            '!' if is_tsubaki else '',
            MonsterHeader.jp_suffix(m)))

    @staticmethod
    def short_with_emoji(m: "MonsterModel", link=True, prefix=None):
        msg = f"{m.monster_no_na} - {m.name_en}"
        return Box(
            prefix,
            Text(get_attribute_emoji_by_monster(m)),
            LinkedText(msg, puzzledragonx(m)) if link else Text(msg),
            Text(MonsterHeader.jp_suffix(m, False)),
            delimiter=' '
        )
