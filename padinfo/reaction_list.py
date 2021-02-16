from typing import List, Optional, TYPE_CHECKING

from discordmenu.emoji.emoji_cache import emoji_cache

from padinfo.core.padinfo_settings import settings
from padinfo.menu.id import IdMenuPanes, IdMenu
from padinfo.view_state.evos import EvosViewState
from padinfo.view_state.materials import MaterialsViewState
from padinfo.view_state.pantheon import PantheonViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


async def get_id_menu_initial_reaction_list(ctx, dgcog, monster: "MonsterModel",
                                            full_reaction_list: List[Optional[str]] = None, force_evoscroll=False):
    # hide some panes if we're in evo scroll mode
    if not full_reaction_list:
        full_reaction_list = [emoji_cache.get_by_name(e) for e in IdMenuPanes.emoji_names()]
    if not force_evoscroll and not settings.checkEvoID(ctx.author.id):
        return full_reaction_list
    alt_versions, gem_versions = await EvosViewState.query(dgcog, monster)
    if alt_versions is None:
        full_reaction_list[full_reaction_list.index(IdMenuPanes.DATA[IdMenu.respond_with_left][0])] = None
        full_reaction_list[full_reaction_list.index(IdMenuPanes.DATA[IdMenu.respond_with_right][0])] = None
        full_reaction_list[full_reaction_list.index(IdMenuPanes.DATA[IdMenu.respond_with_evos][0])] = None
    pantheon_list, series_name = await PantheonViewState.query(dgcog, monster)
    if pantheon_list is None:
        full_reaction_list[full_reaction_list.index(IdMenuPanes.DATA[IdMenu.respond_with_pantheon][0])] = None
    mats, usedin, gemid, gemusedin, skillups, skillup_evo_count, link, gem_override = \
        await MaterialsViewState.query(dgcog, monster)
    if mats is None:
        full_reaction_list[full_reaction_list.index(IdMenuPanes.DATA[IdMenu.respond_with_mats][0])] = None
    return list(filter(None, full_reaction_list))
