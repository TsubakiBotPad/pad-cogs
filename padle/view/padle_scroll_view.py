from math import ceil
from typing import Collection, TYPE_CHECKING

from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.base import Box
from discordmenu.embed.text import BoldText
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.components.config import UserConfig
from tsutils.menu.view.view_state_base import ViewStateBase
from tsutils.query_settings.query_settings import QuerySettings

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel

class PADleScrollViewState(ViewStateBase):
    VIEW_STATE_TYPE: str="PADleScrollView"
    def __init__(self, original_author_id, menu_type, raw_query, title="", all_text=[], current_page=0, extra_state=None,
                 reaction_list = None, message = None):
        super().__init__(original_author_id, menu_type, raw_query,
                         extra_state=extra_state)
        self.all_text = all_text
        self.current_page = current_page
        self.reaction_list = reaction_list
        self.title = title
    
    def get_cur_fields(self):
        fields = []
        for item in range((5*(self.current_page-1)),(5*(self.current_page))):
            if item >= len(self.all_text):
                continue
            fields.append(EmbedField(
                title=f"**Guess #{item+1}**:",
                body=Box(self.all_text[item]),
            ))
        return fields
            
        
    def get_pages_footer(self):
        return "Page " + str(self.current_page) + "/" + str(self.get_num_pages())
    
    def get_num_pages(self):
        return ceil(len(self.all_text) / 5)
    
    def increment_page(self):
        print("Incrementing!")
        if self.current_page < self.get_num_pages() - 1:
            self.current_page = self.current_page + 1
            return
        self.current_page = 0

    def decrement_page(self):
        print("Decrementing!")
        if self.current_page > 0:
            self.current_page = self.current_page - 1
            return
        self.current_page = self.get_num_pages() - 1

class PADleScrollView:
    VIEW_TYPE = 'PADleScroll'
    @staticmethod
    def embed(state: PADleScrollViewState):
        
        fields = state.get_cur_fields()

        return EmbedView(
            EmbedMain(
                title=state.title,
            ),
            embed_footer=embed_footer_with_state(state, text=state.get_pages_footer()),
            embed_fields=fields)