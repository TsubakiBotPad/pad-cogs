from math import ceil
from typing import Collection, TYPE_CHECKING

from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.base import Box
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.components.config import UserConfig
from tsutils.menu.view.view_state_base import ViewStateBase
from tsutils.query_settings.query_settings import QuerySettings

from discordmenu.embed.components import EmbedFooter

from tsutils.tsubaki.links import CLOUDFRONT_URL

TSUBAKI_FLOWER_ICON_URL = CLOUDFRONT_URL + '/tsubaki/tsubakiflower.png'

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel

class PADleScrollViewState(ViewStateBase):
    VIEW_STATE_TYPE: str="PADleScrollView"
    def __init__(self, original_author_id, menu_type, raw_query, title="", all_text=[], current_page=0, extra_state=None,
                 reaction_list = None):
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
    
    @classmethod
    def get_num_pages_ims(self, ims):
        return ceil(len(ims['all_text']) / 5)
    
    @classmethod
    def increment_page(self, ims):
        print("incrementing!")
        if ims['current_page'] < self.get_num_pages_ims(ims) - 1:
            ims['current_page'] = ims['current_page'] + 1
            return
        ims['current_page'] = 0
        
    @classmethod
    def decrement_page(self, ims):
        print("decrementing!")
        if ims['current_page'] > 0:
            ims['current_page'] = ims['current_page'] - 1
            return
        ims['current_page'] = self.get_num_pages_ims(ims) - 1
        
    def serialize(self):
        ret = super().serialize()
        ret.update({
            'all_text': self.all_text,
            'current_page': self.current_page,
            'reaction_list': self.reaction_list,
            'title': self.title,
        })
        return ret

    @classmethod
    async def deserialize(dbcog, _user_config: UserConfig, ims: dict):
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims['reaction_list']
        all_text = ims.get("all_text")
        current_page = ims.get("current_page")
        title = ims.get("title")
        return PADleScrollViewState(original_author_id, menu_type, "", all_text=all_text, current_page=current_page,
                                    title=title, reaction_list=reaction_list)

class PADleScrollView:
    VIEW_TYPE = 'PADleScroll'
    @staticmethod
    def embed(state: PADleScrollViewState):
        
        fields = state.get_cur_fields()
        return EmbedView(
            EmbedMain(
                title=state.title,
            ), # doing embed_footer_with_state() gave me 'form body too long' error ??
            embed_footer=EmbedFooter(
                state.get_pages_footer(),
                icon_url=TSUBAKI_FLOWER_ICON_URL),
            embed_fields=fields)