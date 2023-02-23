from discordmenu.embed.components import EmbedMain, EmbedThumbnail
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterImage
from tsutils.tsubaki.monster_header import MonsterHeader
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class PersonalStatsViewProps:
    def __init__(self, qs: QuerySettings, username: str, played: int, win_rate: float,
                 cur_streak: int, max_streak: int, favorite_monster: "MonsterModel"):
        self.qs = qs
        self.username = username
        self.played = played
        self.win_rate = win_rate
        self.cur_streak = cur_streak
        self.max_streak = max_streak
        self.monster = favorite_monster


class PersonalStatsView:
    VIEW_TYPE = 'PADlePersonalStats'

    @classmethod
    def embed(cls, state: ClosableEmbedViewState, props: PersonalStatsViewProps):
        return EmbedView(
            EmbedMain(
                title=f"{props.username}'s PADle Stats",
                description=(f"**Games Played**: {props.played}\n"
                             f"**Win Rate**: {props.win_rate:.2%}\n"
                             f"**Current Streak**: {props.cur_streak}\n"
                             f"**Max Streak**: {props.max_streak}\n"
                             f"**Favorite Guessed Monster**: {MonsterHeader.menu_title(props.monster).to_markdown()}"),
                color=props.qs.embedcolor),
            embed_thumbnail=EmbedThumbnail(
                MonsterImage.icon(props.monster.monster_id)),
            embed_footer=embed_footer_with_state(
                state, text="Click the X to close.", qs=state.qs))
