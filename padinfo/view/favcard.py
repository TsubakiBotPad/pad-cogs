from typing import List, TYPE_CHECKING

from discordmenu.embed.components import EmbedMain, EmbedThumbnail
from discordmenu.embed.view import EmbedView
from discordmenu.embed.view_state import ViewState
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.common import get_monster_from_ims
from padinfo.view.components.evo_scroll_mixin import EvoScrollView, MonsterEvolution, EvoScrollViewState

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class FavcardViewState(ViewState, EvoScrollViewState):
    VIEW_STATE_TYPE = "Favcard"

    def __init__(self, original_author_id, menu_type, raw_query, query, monster: "MonsterModel",
                 alt_monsters: List[MonsterEvolution], query_settings: QuerySettings,
                 extra_state=None
                 ):
        super().__init__(original_author_id, menu_type, raw_query,
                         extra_state=extra_state)
        self.query_settings = query_settings
        self.alt_monsters = self.alt_monster_order_pref(alt_monsters, query_settings)
        self.alt_monster_ids = self.alt_monster_ids(self.alt_monsters)
        self.monster = monster
        self.query = query

    def serialize(self):
        ret = super().serialize()
        ret.update({
            "query": self.query,
            "resolved_monster_id": self.monster.monster_id,
            "query_settings": self.query_settings.serialize(),
        })
        return ret

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
        query_settings = QuerySettings.deserialize(ims.get('query_settings'))
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']

        return FavcardViewState(original_author_id, menu_type, raw_query, query, monster,
                                alt_monsters, query_settings, extra_state=ims)


class FavcardView(EvoScrollView):
    VIEW_TYPE = "Favcard"

    @classmethod
    def embed(cls, state: FavcardViewState):
        m = state.monster
        qs = state.query_settings
        fields = [
            cls.evos_embed_field(state)
        ]
        return EmbedView(
            EmbedMain(
                color=qs.embedcolor,
                title=MonsterHeader.menu_title(m).to_markdown(),
                url=MonsterLink.header_link(m, qs)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m.monster_id)),
            embed_footer=embed_footer_with_state(state, qs=qs),
            embed_fields=fields
        )
