from typing import TYPE_CHECKING, List

from discordmenu.embed.components import EmbedMain, EmbedThumbnail
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.view_state_base import ViewStateBase
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterLink, MonsterImage
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.components.evo_scroll_mixin import EvoScrollView, EvoScrollViewState, MonsterEvolution

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class DroplocQueriedProps:
    def __init__(self, monster: "MonsterModel", alt_monsters: List[MonsterEvolution],
                 subdungeons, dungeons):
        self.monster = monster
        self.alt_monsters = alt_monsters
        self.subdungeons = subdungeons
        self.dungeons = dungeons


class DroplocViewState(ViewStateBase, EvoScrollViewState):
    VIEW_STATE_TYPE = "Droploc"

    def __init__(self, original_author_id, menu_type, query, query_settings: QuerySettings,
                 monster_id: int,
                 queried_props: DroplocQueriedProps,
                 display: str = 'expand',
                 extra_state=None):
        super().__init__(original_author_id, menu_type, query,
                         extra_state=extra_state)
        self.monster_id = monster_id
        self.queried_props = queried_props
        self.monster = self.queried_props.monster
        self.alt_monsters = self.queried_props.alt_monsters
        self.display = display
        self.query_settings = query_settings

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'monster_id': self.monster_id,
            'query_settings': self.query_settings.serialize(),
            'display': self.display,
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        query_settings = QuerySettings.deserialize(ims.get('query_settings'))
        display = ims['display']
        monster_id = ims['monster_id']
        queried_props = await cls.query(monster_id, dbcog)

        return cls(original_author_id, menu_type, query,
                   query_settings, monster_id, queried_props, display)

    @staticmethod
    async def query(monster_id, dbcog):
        graph = dbcog.database.graph
        monster = await graph.get_monster(monster_id)
        alt_monsters = graph.get_alt_monsters(monster)
        evolutions = [MonsterEvolution(m, graph.get_evolution(m)) for m in alt_monsters]
        subdungeons = dbcog.database.dungeon.get_subdungeons_from_drop_monster(monster)
        dungeons = dbcog.database.dungeon.get_dungeon_mapping(subdungeons)
        props = DroplocQueriedProps(monster, evolutions, subdungeons, dungeons)
        return props

    @staticmethod
    def expand(ims):
        ims['display'] = 'expand'

    @staticmethod
    def contract(ims):
        ims['display'] = 'contract'


class DroplocView(EvoScrollView):
    VIEW_TYPE = "Droploc"

    @classmethod
    def embed(cls, state: DroplocViewState):
        m = state.queried_props.monster

        fields = [
            cls.evos_embed_field(state)
        ]

        return EmbedView(
            EmbedMain(
                color=state.query_settings.embedcolor,
                title=MonsterHeader.menu_title(m),
                url=MonsterLink.header_link(m, state.query_settings)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(m.monster_id)),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
