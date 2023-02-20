from typing import List, TYPE_CHECKING, Optional

from discordmenu.embed.components import EmbedMain, EmbedThumbnail, EmbedField
from discordmenu.embed.view import EmbedView
from discordmenu.embed.view_state import ViewState
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.pad_view import PadView
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.common import get_monster_from_ims
from padinfo.view.components.evo_scroll_mixin import EvoScrollView, MonsterEvolution, EvoScrollViewState
from padinfo.view.components.padinfo_view import PadinfoView, PadinfoViewState

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class FavcardViewState(PadinfoViewState, EvoScrollViewState):
    VIEW_STATE_TYPE = "Favcard"

    def __init__(self, original_author_id, menu_type, raw_query, query, qs: QuerySettings, monster: "MonsterModel",
                 alt_monsters: List[MonsterEvolution],
                 extra_state=None
                 ):
        super().__init__(original_author_id, menu_type, raw_query, query, qs, monster,
                         extra_state=extra_state)
        self.alt_monsters = self.alt_monster_order_pref(alt_monsters, qs)
        self.alt_monster_ids = self.alt_monster_ids(self.alt_monsters)

    @staticmethod
    async def set_favcard(dbcog, ims):
        async with dbcog.config.user_from_id(ims["original_author_id"]).fm_flags() as fm_flags:
            fm_flags['favcard'] = ims["resolved_monster_id"]

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

        return FavcardViewState(original_author_id, menu_type, raw_query, query, qs, monster,
                                alt_monsters, extra_state=ims)


class FavcardView(PadinfoView, EvoScrollView):
    VIEW_TYPE = "Favcard"

    @classmethod
    def embed_fields(cls, state: FavcardViewState) -> List[EmbedField]:
        return [
            cls.evos_embed_field(state)
        ]

    @classmethod
    def embed_thumbnail(cls, state: FavcardViewState) -> Optional[EmbedThumbnail]:
        return EmbedThumbnail(MonsterImage.icon(state.monster.monster_id))
