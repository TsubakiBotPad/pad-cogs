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
    VIEW_STATE_TYPE: str="PADleScrollView"
    def __init__(self, original_author_id, menu_type, raw_query, dbcog, monster, cur_day_guesses={}, current_page=0, extra_state=None,
                 reaction_list = None, current_day:int=0,):
        super().__init__(original_author_id, menu_type, raw_query,
                         extra_state=extra_state)
        self.cur_day_guesses = cur_day_guesses
        self.current_page = current_page
        self.reaction_list = reaction_list
        self.current_day = current_day
        self.dbcog = dbcog
        self.monster = monster
    
    def get_cur_fields(self):
        fields = []
        for item in range((5*(self.current_page-1)),(5*(self.current_page))):
            if item >= len(self.cur_day_guesses):
                continue
            guessed_mon = MonsterDiff(self.monster, self.dbcog.get_monster(int(self.cur_day_guesses[item])))
            fields.append(EmbedField(
                title=f"**Guess #{item+1}**:",
                body=Box("\n".join([guessed_mon.get_name_line_feedback_text(), guessed_mon.get_other_info_feedback_text(), guessed_mon.get_awakenings_feedback_text()])),
            ))
        return fields
            
        
    def get_pages_footer(self):
        return "Page " + str(self.current_page) + "/" + str(self.get_num_pages())
    
    def get_num_pages(self):
        return ceil(len(self.cur_day_guesses) / 5)
        
    def serialize(self):
        ret = super().serialize()
        ret.update({
            'current_page': self.current_page,
            'reaction_list': self.reaction_list,
            'current_day': self.current_day,
            'cur_monster': self.monster.monster_id,
        })
        return ret

    @classmethod
    async def deserialize(dbcog, _user_config: UserConfig, ims: dict, all_guesses):
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims['reaction_list']
        current_page = ims['current_page']
        current_day = ims['current_day']
        cur_monster = ims['cur_monster']
        monster = dbcog.get_monster(int(cur_monster))
        cur_day_guesses = all_guesses[current_day]
        return PADleScrollViewState(original_author_id, menu_type, "", current_page=current_page,
                                    current_day=current_day, reaction_list=reaction_list, dbcog=dbcog,
                                    cur_day_guesses=cur_day_guesses, monster=monster)

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