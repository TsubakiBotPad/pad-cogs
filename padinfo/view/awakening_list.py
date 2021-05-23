from typing import List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.config import UserConfig
from padinfo.view.common import get_awoken_skill_description
from padinfo.view.components.view_state_base import ViewStateBase


class AwakeningListSortTypes:
    alphabetical = "Alphabetical"
    numerical = "Numerical"


class AwakeningListViewState(ViewStateBase):
    MAX_ITEMS_PER_PANE = 10

    def __init__(self, original_author_id, menu_type, color, sort_type, paginated_skills, current_page,
                 extra_state=None,
                 reaction_list: List[str] = None):
        super().__init__(original_author_id, menu_type, '', extra_state=extra_state, reaction_list=reaction_list)
        self.sort_type = sort_type
        self.paginated_skills = paginated_skills
        self.total_pages = len(self.paginated_skills)
        self.current_page = current_page
        self.color = color

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'current_page': self.current_page,
            'total_pages': self.total_pages,
            'sort_type': self.sort_type,
        })
        return ret

    @classmethod
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict):
        sort_type = ims['sort_type']
        paginated_skills = await cls.query(dgcog, sort_type)
        original_author_id = ims['original_author_id']
        current_page = ims['current_page']
        menu_type = ims['menu_type']
        reaction_list = ims['reaction_list']
        return AwakeningListViewState(original_author_id, menu_type, user_config.color, sort_type, paginated_skills,
                                      current_page, reaction_list=reaction_list)

    @classmethod
    async def query(cls, dgcog, sort_type):
        awoken_skills = dgcog.database.get_all_awoken_skills()
        if sort_type == AwakeningListSortTypes.alphabetical:
            awoken_skills = sorted(awoken_skills, key=lambda awo: awo.name_en)
        elif sort_type == AwakeningListSortTypes.numerical:
            awoken_skills = sorted(awoken_skills, key=lambda awo: awo.awoken_skill_id)

        paginated_skills = [awoken_skills[i:i + AwakeningListViewState.MAX_ITEMS_PER_PANE]
                            for i in range(0, len(awoken_skills), AwakeningListViewState.MAX_ITEMS_PER_PANE)]
        return paginated_skills


class AwakeningListView:
    VIEW_TYPE = 'AwakeningList'

    @staticmethod
    def embed(state: AwakeningListViewState):
        fields = [
            EmbedField('Awakenings - by {}'.format('name' if state.sort_type == AwakeningListSortTypes.alphabetical else 'id number'),
                       Box(*[get_awoken_skill_description(awo) for awo in state.paginated_skills[state.current_page]])),
            EmbedField('Page', Box(
                '{} of {}'.format(str(state.current_page + 1), str(len(state.paginated_skills)))
            ))
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
