from abc import abstractmethod
from typing import List, TYPE_CHECKING, Optional

from discord.types.embed import EmbedField
from discordmenu.embed.components import EmbedThumbnail
from discordmenu.embed.view_state import ViewState
from tsutils.menu.components.config import UserConfig
from tsutils.menu.pad_view import PadViewState, PadView
from tsutils.query_settings.enums import AltEvoSort
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterImage
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.common import get_monster_from_ims
from padinfo.view.components.evo_scroll_mixin import EvoScrollViewState, MonsterEvolution
from padinfo.view.components.padinfo_view import PadinfoView, PadinfoViewState

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class ViewStateBaseId(PadViewState, EvoScrollViewState):
    def __init__(self, original_author_id, menu_type, raw_query, query, qs, monster: "MonsterModel",
                 alt_monsters: List[MonsterEvolution], is_jp_buffed: bool,
                 reaction_list: List[str] = None,
                 extra_state=None):
        super().__init__(original_author_id=original_author_id, menu_type=menu_type, raw_query=raw_query, query=query,
                         qs=qs,
                         extra_state=extra_state)
        self.reaction_list = reaction_list
        self.monster = monster
        self.is_jp_buffed = is_jp_buffed
        self.query = query

        self.alt_monsters = self.alt_monster_order_pref(alt_monsters, qs)
        self.alt_monster_ids = self.alt_monster_ids(self.alt_monsters)

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'qs': self.qs.serialize(),
            'resolved_monster_id': self.monster.monster_id,
            'reaction_list': self.reaction_list,
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        monster = await get_monster_from_ims(dbcog, ims)

        alt_monsters = cls.get_alt_monsters_and_evos(dbcog, monster)

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        qs = QuerySettings.deserialize(ims.get('qs'))
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)

        return cls(original_author_id, menu_type, raw_query, query, qs, monster,
                   alt_monsters, is_jp_buffed,
                   reaction_list=reaction_list,
                   extra_state=ims)


class IdBaseView(PadinfoView):
    TSUBAKI = 2141

    @classmethod
    def embed_title(cls, state: ViewStateBaseId) -> Optional[str]:
        m = state.monster
        return MonsterHeader.menu_title(m,
                                        is_tsubaki=state.alt_monsters[0].monster.monster_id == cls.TSUBAKI,
                                        is_jp_buffed=state.is_jp_buffed).to_markdown()

    @classmethod
    @abstractmethod
    def embed_fields(cls, state: ViewStateBaseId) -> List[EmbedField]:
        ...
