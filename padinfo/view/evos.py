from typing import List, TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.config import UserConfig
from padinfo.common.external_links import puzzledragonx
from padinfo.view.base import BaseIdView
from padinfo.view.common import get_monster_from_ims
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.components.view_state_base_id import ViewStateBaseId, MonsterEvolution

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class EvosViewState(ViewStateBaseId):
    def __init__(self, original_author_id, menu_type, raw_query, query, color,
                 monster: "MonsterModel", alt_monsters: List[MonsterEvolution],
                 alt_versions: List["MonsterModel"], gem_versions: List["MonsterModel"],
                 reaction_list: List[str] = None,
                 use_evo_scroll: bool = True,
                 extra_state=None):
        super().__init__(original_author_id, menu_type, raw_query, query, color, monster, alt_monsters,
                         use_evo_scroll=use_evo_scroll,
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
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        monster = await get_monster_from_ims(dgcog, ims)
        alt_versions, gem_versions = await EvosViewState.query(dgcog, monster)

        if alt_versions is None:
            return None
        alt_monsters = cls.get_alt_monsters_and_evos(dgcog, monster)
        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        use_evo_scroll = ims.get('use_evo_scroll') != 'False'
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')

        return cls(original_author_id, menu_type, raw_query, query, user_config.color,
                   monster,
                   alt_monsters,
                   alt_versions, gem_versions,
                   reaction_list=reaction_list,
                   use_evo_scroll=use_evo_scroll,
                   extra_state=ims)

    @staticmethod
    async def query(dgcog, monster):
        db_context = dgcog.database
        alt_versions = sorted(db_context.graph.get_alt_monsters_by_id(monster.monster_id),
                              key=lambda x: x.monster_id)
        gem_versions = list(filter(None, map(db_context.graph.evo_gem_monster, alt_versions)))
        if len(alt_versions) == 1 and len(gem_versions) == 0:
            return None, None
        return alt_versions, gem_versions


class EvosView(BaseIdView):
    VIEW_TYPE = 'Evos'

    @staticmethod
    def _evo_lines(monsters, current_monster):
        if not len(monsters):
            return []
        return [
            MonsterHeader.short_with_emoji(ae, link=ae.monster_id != current_monster.monster_id)
            for ae in sorted(monsters, key=lambda x: int(x.monster_id))
        ]

    @classmethod
    def embed(cls, state: EvosViewState):
        fields = [
            EmbedField(
                ("{} evolution" if len(state.alt_versions) == 1 else "{} evolutions").format(len(state.alt_versions)),
                Box(*EvosView._evo_lines(state.alt_versions, state.monster)))]

        if state.gem_versions:
            fields.append(
                EmbedField(
                    ("{} evolve gem" if len(state.gem_versions) == 1 else "{} evolve gems").format(
                        len(state.gem_versions)),
                    Box(*EvosView._evo_lines(state.gem_versions, state.monster))))

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_maybe_tsubaki(state.monster,
                                                       state.alt_monsters[0].monster.monster_id == cls.TSUBAKI
                                                       ).to_markdown(),
                url=puzzledragonx(state.monster)),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(state.monster)),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields)
