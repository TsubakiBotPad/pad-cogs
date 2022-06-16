from typing import TYPE_CHECKING
from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.menu.components.footers import embed_footer_with_state
from discordmenu.embed.view import EmbedView
from discordmenu.embed.components import EmbedMain, EmbedThumbnail
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterImage
from tsutils.tsubaki.monster_header import MonsterHeader
if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class ClosableStatsViewProps:
    def __init__(self, query_settings: QuerySettings, username: str, played: int, win_rate: float,
                 cur_streak: int, max_streak: int, favorite_monster: "MonsterModel"):
        self.query_settings = query_settings
        self.username = username
        self.played = played
        self.win_rate = win_rate
        self.cur_streak = cur_streak
        self.max_streak = max_streak
        self.monster = favorite_monster
        

class ClosableStatsView:
    VIEW_TYPE = 'PADleStats'

    @classmethod
    def embed(cls, state: ClosableEmbedViewState, props: ClosableStatsViewProps):
       return EmbedView(
            EmbedMain(
                title=f"{props.username}'s PADle Stats",
                description=(f"**Games Played**: {props.played}\n"
                             f"**Win Rate**: {props.win_rate:.2%}\n"
                             f"**Current Streak**: {props.cur_streak}\n"
                             f"**Max Streak**: {props.max_streak}\n"
                             f"**Favorite Guessed Monster**: {MonsterHeader.menu_title(props.monster).to_markdown()}"),
                color=props.query_settings.embedcolor),
            embed_thumbnail=EmbedThumbnail(
                MonsterImage.icon(props.monster.monster_id)),
            embed_footer=embed_footer_with_state(state, text="Click the X to close."))
       