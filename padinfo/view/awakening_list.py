from typing import List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.config import UserConfig
from padinfo.view.common import get_awoken_skill_description
from padinfo.view.components.view_state_base import ViewStateBase


class AwakeningListViewState(ViewStateBase):
    MAX_ITEMS_PER_PANE = 5

    def __init__(self, original_author_id, menu_type, color, sort_type, paginated_skills, page,
                 extra_state=None,
                 reaction_list: List[str] = None):
        super().__init__(original_author_id, menu_type, '', extra_state=extra_state, reaction_list=reaction_list)
        self.sort_type = sort_type
        self.paginated_skills = paginated_skills
        self.total_pages = len(self.paginated_skills)
        self.page = page
        self.color = color

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'page': self.page,
            'total_pages': self.total_pages,
        })

    @classmethod
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict):
        sort_type = ims['sort_type']
        paginated_skills = await cls.query(dgcog, sort_type)
        original_author_id = ims['original_author_id']
        page = ims['page']
        menu_type = ims['menu_type']
        return AwakeningListViewState(original_author_id, menu_type, user_config.color, sort_type, paginated_skills,
                                      page)

    @classmethod
    async def query(cls, dgcog, sort_type):
        awoken_skills = dgcog.database.get_all_awoken_skills()
        if sort_type == 'alphabetical':
            awoken_skills = sorted(awoken_skills, key=lambda awo: awo.name_en)
        elif sort_type == 'numerical':
            awoken_skills = sorted(awoken_skills, key=lambda awo: awo.awoken_skill_id)
        else:
            raise KeyError('Invalid sort type for awoken skills')
        paginated_skills = [awoken_skills[i:i + AwakeningListViewState.MAX_ITEMS_PER_PANE]
                            for i in range(0, len(awoken_skills), AwakeningListViewState.MAX_ITEMS_PER_PANE)]
        return paginated_skills


class AwakeningListView:
    VIEW_TYPE = 'AwakeningList'

    @staticmethod
    def embed(state: AwakeningListViewState):
        fields = [
            EmbedField('Awakenings',
                       Box(*[get_awoken_skill_description(awo) for awo in state.paginated_skills[state.page]])),
            EmbedField('Page', Box(
                '{} of {}'.format(str(state.page), str(len(state.paginated_skills)))
            ))
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
