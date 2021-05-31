from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.text import LinkedText, Text

from padinfo.common.emoji_map import get_attribute_emoji_by_monster
from padinfo.common.external_links import puzzledragonx

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class MonsterHeader:
    @classmethod
    def jp_suffix(cls, m: "MonsterModel", discrepant=False, subname_on_override=True):
        suffix = ""
        if m.roma_subname and (subname_on_override or m.name_en_override is None):
            suffix += ' [{}]'.format(m.roma_subname)
        if not m.on_na:
            suffix += ' (JP only)'
        if discrepant:
            suffix += ' (JP buffed)'
        return suffix

    @classmethod
    def short(cls, m: "MonsterModel", link=False):
        type_emojis = ''
        msg = '[{}] {}{}'.format(m.monster_no_na, type_emojis, m.name_en)
        return '[{}]({})'.format(msg, puzzledragonx(m)) if link else msg

    @classmethod
    def long(cls, m: "MonsterModel", link=False):
        msg = cls.short(m) + cls.jp_suffix(m)
        return '[{}]({})'.format(msg, puzzledragonx(m)) if link else msg

    @classmethod
    def name(cls, m: "MonsterModel", link=False, show_jp=False):
        msg = '[{}] {}{}'.format(
            m.monster_no_na,
            m.name_en,
            cls.jp_suffix(m) if show_jp else '')
        return LinkedText(msg, puzzledragonx(m)) if link else Text(msg)

    @classmethod
    def long_v2(cls, m: "MonsterModel", link=False):
        msg = '[{}] {}{}'.format(m.monster_no_na, m.name_en, cls.jp_suffix(m))
        return LinkedText(msg, puzzledragonx(m)) if link else Text(msg)

    @classmethod
    def long_maybe_tsubaki(cls, m: "MonsterModel", is_tsubaki, discrepant=False):
        """Returns long_v2 as well as an `!` if the monster is Tsubaki
    
        To celebrate 1000 issues/PRs in our main Tsubaki repo, we added this easter egg! Yay!
        """
        return '[{}] {}{}{}'.format(
            m.monster_no_na,
            m.name_en,
            '!' if is_tsubaki else '',
            cls.jp_suffix(m, discrepant))

    @classmethod
    def fmt_id_header(cls, m: "MonsterModel", is_tsubaki, discrepant):
        return Text('{} {}'.strip().format(
            '\N{EARTH GLOBE AMERICAS}' if m.server_priority == "NA" else '',
            cls.long_maybe_tsubaki(m, is_tsubaki, bool(discrepant))))

    @classmethod
    def short_with_emoji(cls, m: "MonsterModel", link=True, prefix=None):
        msg = f"{m.monster_no_na} - {m.name_en}"
        return Box(
            prefix,
            Text(get_attribute_emoji_by_monster(m)),
            LinkedText(msg, puzzledragonx(m)) if link else Text(msg),
            Text(cls.jp_suffix(m, False, False)),
            delimiter=' '
        )
