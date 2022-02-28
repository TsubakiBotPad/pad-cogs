from typing import TYPE_CHECKING, Optional

from discordmenu.embed.base import Box
from discordmenu.embed.text import LinkedText, Text
from tsutils.enums import Server
from tsutils.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterLink

from padinfo.common.emoji_map import get_attribute_emoji_by_monster

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


# TODO: add query_settings to all uses
class MonsterHeader:
    @classmethod
    def jp_suffix(cls, m: "MonsterModel", is_jp_buffed=False, subname_on_override=True):
        suffix = ""
        if m.roma_subname and (subname_on_override or m.name_en_override is None):
            suffix += ' [{}]'.format(m.roma_subname)
        if not m.on_na:
            suffix += ' (JP only)'
        if is_jp_buffed:
            suffix += ' (JP buffed)'
        return suffix

    @classmethod
    def short(cls, m: "MonsterModel", link=False, query_settings: Optional[QuerySettings] = None):
        type_emojis = ''
        msg = '[{}] {}{}'.format(m.monster_no_na, type_emojis, m.name_en)
        return '[{}]({})'.format(msg, MonsterLink.header_link(m, query_settings=query_settings)) if link else msg

    @classmethod
    def long(cls, m: "MonsterModel", link=False, query_settings: Optional[QuerySettings] = None):
        msg = cls.short(m) + cls.jp_suffix(m)
        return '[{}]({})'.format(msg, MonsterLink.header_link(m, query_settings=query_settings)) if link else msg

    @classmethod
    def name(cls, m: "MonsterModel", link=False, show_jp=False,
             query_settings: Optional[QuerySettings] = None):
        msg = '[{}] {}{}'.format(
            m.monster_no_na,
            m.name_en,
            cls.jp_suffix(m) if show_jp else '')
        return LinkedText(msg, MonsterLink.header_link(m, query_settings=query_settings)) if link else Text(msg)

    @classmethod
    def long_v2(cls, m: "MonsterModel", link=False,
                query_settings: Optional[QuerySettings] = None):
        msg = '[{}] {}{}'.format(m.monster_no_na, m.name_en, cls.jp_suffix(m))
        return LinkedText(msg, MonsterLink.header_link(m, query_settings=query_settings)) if link else Text(msg)

    @classmethod
    def long_maybe_tsubaki(cls, m: "MonsterModel", is_tsubaki, is_jp_buffed=False,
                           query_settings: Optional[QuerySettings] = None):
        """Returns long_v2 as well as an `!` if the monster is Tsubaki
    
        To celebrate 1000 issues/PRs in our main Tsubaki repo, we added this easter egg! Yay!
        """
        return '[{}] {}{}{}'.format(
            m.monster_no_na,
            m.name_en,
            '!' if is_tsubaki else '',
            cls.jp_suffix(m, is_jp_buffed))

    @classmethod
    def fmt_id_header(cls, m: "MonsterModel", is_tsubaki=False, is_jp_buffed=False,
                      use_emoji=False):
        return Text('{}{} {}'.strip().format(
            get_attribute_emoji_by_monster(m) if use_emoji else '',
            '\N{EARTH GLOBE AMERICAS}' if m.server_priority == Server.NA else '',
            cls.long_maybe_tsubaki(m, is_tsubaki, bool(is_jp_buffed))))

    @classmethod
    def short_with_emoji(cls, m: "MonsterModel", link=True, prefix=None,
                         query_settings: Optional[QuerySettings] = None):
        msg = f"{m.monster_no_na} - {m.name_en}"
        suffix = cls.jp_suffix(m, False, False)
        return Box(
            prefix,
            Text(get_attribute_emoji_by_monster(m)),
            LinkedText(msg, MonsterLink.header_link(m, query_settings=query_settings)) if link else Text(msg),
            Text(suffix) if suffix else None,
            delimiter=' '
        )
