from math import ceil
from typing import Collection, TYPE_CHECKING

from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.base import Box
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.components.config import UserConfig
from tsutils.menu.view.view_state_base import ViewStateBase
from tsutils.query_settings.query_settings import QuerySettings
from padle.monsterdiff import MonsterDiff

from discordmenu.embed.components import EmbedFooter

from tsutils.tsubaki.links import CLOUDFRONT_URL

TSUBAKI_FLOWER_ICON_URL = CLOUDFRONT_URL + '/tsubaki/tsubakiflower.png'

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class PADleScrollViewState(ViewStateBase):
    VIEW_STATE_TYPE: str = "PADleScrollView"

    def __init__(self, original_author_id, menu_type, raw_query="", monster=None, cur_day_page_guesses=[],
                 current_page=0, extra_state=None, reaction_list=None, current_day: int = 0, num_pages=0):
        super().__init__(original_author_id, menu_type, raw_query,
                         extra_state=extra_state)
        self.cur_day_page_guesses = cur_day_page_guesses
        self.current_page = current_page
        self.reaction_list = reaction_list
        self.current_day = current_day
        self.monster = monster
        self.num_pages = num_pages

    def get_cur_fields(self):
        fields = []
        for index, item in enumerate(self.cur_day_page_guesses):
            guessed_mon = MonsterDiff(self.monster, item)
            fields.append(EmbedField(
                title=f"**Guess #{5 * (self.current_page) + index + 1}**:",
                body=Box("\n".join(
                    [guessed_mon.get_name_line_feedback_text(), guessed_mon.get_other_info_feedback_text(),
                     guessed_mon.get_awakenings_feedback_text()])),
            ))
        return fields

    @classmethod
    async def do_queries(cls, dbcog, guess_ids):
        monster_list = []
        for id in guess_ids:
            monster_list.append(dbcog.get_monster(int(id)))
        return monster_list

    def get_pages_footer(self):
        return "Page " + str(self.current_page + 1) + "/" + str(self.num_pages)

    @classmethod
    def get_monster_ids_list(cls, monster_list):
        ids = []
        for monster in monster_list:
            ids.append(monster.monster_id)
        return ids

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'current_page': self.current_page,
            'reaction_list': self.reaction_list,
            'current_day': self.current_day,
            'cur_monster': self.monster.monster_id,
            'num_pages': self.num_pages
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, _user_config: UserConfig, todays_guesses, ims: dict):
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims['reaction_list']
        cur_page = ims['current_page']
        current_day = ims['current_day']
        cur_monster = ims['cur_monster']
        num_pages = ims['num_pages']
        monster = dbcog.get_monster(int(cur_monster))
        cur_day_page_guesses = await cls.do_queries(dbcog, todays_guesses[((cur_page) * 5):((cur_page + 1) * 5)])
        return PADleScrollViewState(original_author_id, menu_type, "", current_page=cur_page,
                                    current_day=current_day, reaction_list=reaction_list,
                                    cur_day_page_guesses=cur_day_page_guesses, monster=monster, num_pages=num_pages)


class PADleScrollView:
    VIEW_TYPE = 'PADleScroll'

    @staticmethod
    def embed(state: PADleScrollViewState):
        fields = state.get_cur_fields()
        return EmbedView(
            EmbedMain(
                title=f"**PADle #{state.current_day}**",
            ),
            embed_footer=embed_footer_with_state(state, text=state.get_pages_footer()),
            embed_fields=fields)
