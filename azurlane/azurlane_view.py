from typing import Collection, TYPE_CHECKING

from discordmenu.embed.components import EmbedBodyImage, EmbedMain
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.view_state_base import ViewStateBase
from tsutils.query_settings.query_settings import QuerySettings

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel

ORDINAL_WORDS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth']


class AzurlaneViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, query_settings: QuerySettings,
                 c, image_idx,
                 extra_state=None, reaction_list=None
                 ):
        super().__init__(original_author_id, menu_type, '', extra_state=extra_state, reaction_list=reaction_list)
        self.query_settings = query_settings
        self.menu_type = menu_type
        self.image_idx = image_idx
        self.c = c

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'idx': self.c['id'],
            'query_settings': self.query_settings.serialize(),
            'current_index': self.image_idx,
        })
        return ret

    @classmethod
    async def deserialize(cls, alcog, _user_config: UserConfig, ims: dict):
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        query_settings = QuerySettings.deserialize(ims.get('qs'))
        reaction_list = ims['reaction_list']
        image_idx = ims['current_index']

        card = alcog.id_to_card[ims['idx']]
        return AzurlaneViewState(original_author_id, menu_type, query_settings, card, image_idx,
                                 reaction_list=reaction_list)


class AzurlaneView:
    VIEW_TYPE = 'Azurlane'

    @staticmethod
    def get_count(arr: Collection["MonsterModel"], *elements: "MonsterModel") -> str:
        if not arr:
            return "N/A"
        count = sum(1 for m in arr if m in elements)
        if count == 0:
            return "0"
        return f"{round(100 * count / len(arr), 3)}%"

    @classmethod
    def embed(cls, state: AzurlaneViewState):
        c = state.c

        cid = c['id']
        name = c['name_en']
        image = c['images'][state.image_idx]
        image_title = image['title']

        url = image['url']

        return EmbedView(
            EmbedMain(
                color=state.query_settings.embedcolor,
                title=f'[{cid}] {name} - {image_title}',
                url=url
            ),
            embed_body_image=EmbedBodyImage(url),
            embed_footer=embed_footer_with_state(state, qs=state.query_settings)
        )
