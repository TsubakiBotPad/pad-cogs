from typing import TYPE_CHECKING, Optional

from tsutils.query_settings import QuerySettings

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
    def name(cls, m: "MonsterModel", link=False, show_jp=False,
             query_settings: Optional[QuerySettings] = None):
        msg = '[{}] {}{}'.format(
            m.monster_no_na,
            m.name_en,
            cls.jp_suffix(m) if show_jp else '')
