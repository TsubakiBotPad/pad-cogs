from typing import List, TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedField, EmbedMain, EmbedThumbnail
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.base import BaseIdView
from padinfo.view.common import get_monster_from_ims
from padinfo.view.components.evo_scroll_mixin import MonsterEvolution
from padinfo.view.components.view_state_base_id import ViewStateBaseId, IdBaseView

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class EvosViewState(ViewStateBaseId):
    def __init__(self, original_author_id, menu_type, raw_query, query, qs: QuerySettings,
                 monster: "MonsterModel",
                 alt_monsters: List[MonsterEvolution], is_jp_buffed: bool,
                 alt_versions: List["MonsterModel"], gem_versions: List["MonsterModel"],
                 reaction_list: List[str] = None,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, qs, query, monster,
                         alt_monsters, is_jp_buffed,
                         reaction_list=reaction_list,
                         extra_state=extra_state)
        self.alt_versions = alt_versions
        self.gem_versions = gem_versions

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': EvosView.VIEW_TYPE,
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        monster = await get_monster_from_ims(dbcog, ims)
        alt_versions, gem_versions = await EvosViewState.do_query(dbcog, monster)

        if alt_versions is None:
            return None
        alt_monsters = cls.get_alt_monsters_and_evos(dbcog, monster)
        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        query_settings = QuerySettings.deserialize(ims.get('qs'))
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(monster)

        return cls(original_author_id, menu_type, raw_query, query, monster,
                   alt_monsters, is_jp_buffed, query_settings,
                   alt_versions, gem_versions,
                   reaction_list=reaction_list,
                   extra_state=ims)

    @staticmethod
    async def do_query(dbcog, monster):
        db_context = dbcog.database
        alt_versions = sorted(db_context.graph.get_alt_monsters(monster),
                              key=lambda x: x.monster_id)
        gem_versions = list(filter(None, map(db_context.graph.evo_gem_monster, alt_versions)))
        if len(alt_versions) == 1 and len(gem_versions) == 0:
            return None, None
        return alt_versions, gem_versions


class EvosView(IdBaseView):
    VIEW_TYPE = 'Evos'

    @staticmethod
    def _evo_lines(monsters, current_monster, query_settings):
        if not len(monsters):
            return []
        return [
            MonsterHeader.box_with_emoji(ae, link=ae.monster_id != current_monster.monster_id, query_settings=query_settings)
            for ae in sorted(monsters, key=lambda x: int(x.monster_id))
        ]

    @classmethod
    def embed_fields(cls, state: EvosViewState) -> List[EmbedField]:
        fields = [
            EmbedField(
                ("{} evolution" if len(state.alt_versions) == 1 else "{} evolutions").format(len(state.alt_versions)),
                Box(*EvosView._evo_lines(state.alt_versions, state.monster, state.qs)))]

        if state.gem_versions:
            fields.append(
                EmbedField(
                    ("{} evolve gem" if len(state.gem_versions) == 1 else "{} evolve gems").format(
                        len(state.gem_versions)),
                    Box(*EvosView._evo_lines(
                        state.gem_versions, state.monster, state.qs))))
        return fields
