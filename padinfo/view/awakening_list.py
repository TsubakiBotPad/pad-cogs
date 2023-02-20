from typing import List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedField, EmbedMain
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.pad_view import PadViewState, PadView
from tsutils.menu.view.view_state_base import ViewStateBase
from tsutils.query_settings.query_settings import QuerySettings

from padinfo.view.common import get_awoken_skill_description


class AwakeningListSortTypes:
    alphabetical = "Alphabetical"
    numerical = "Numerical"


class AwakeningListViewState(PadViewState):
    MAX_ITEMS_PER_PANE = 10

    def __init__(self, original_author_id, menu_type, qs: QuerySettings,
                 sort_type, paginated_skills, current_page,
                 token_map: dict,
                 extra_state=None,
                 reaction_list: List[str] = None):
        super().__init__(original_author_id, menu_type, '', '', qs, extra_state=extra_state)
        self.sort_type = sort_type
        self.paginated_skills = paginated_skills
        self.total_pages = len(self.paginated_skills)
        self.current_page = current_page
        self.qs = qs
        self.reaction_list = reaction_list

        # this is the list of allowed modifiers from token_mappings dbcog file (cannot import it bc redbot rules)
        self.token_map = {}
        for k in token_map.keys():
            self.token_map[k.value] = token_map[k]

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'current_page': self.current_page,
            'total_pages': self.total_pages,
            'sort_type': self.sort_type,
            'reaction_list': self.reaction_list,
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, _user_config: UserConfig, ims: dict):
        sort_type = ims['sort_type']
        paginated_skills = await cls.do_query(dbcog, sort_type)
        original_author_id = ims['original_author_id']
        current_page = ims['current_page']
        menu_type = ims['menu_type']
        reaction_list = ims['reaction_list']
        token_map = dbcog.AWOKEN_SKILL_TOKEN_MAP
        query_settings = QuerySettings.deserialize(ims.get('qs'))
        return AwakeningListViewState(original_author_id, menu_type, query_settings, sort_type, paginated_skills,
                                      current_page, token_map, reaction_list=reaction_list)

    @classmethod
    async def do_query(cls, dbcog, sort_type):
        awoken_skills = dbcog.database.get_all_awoken_skills()
        if sort_type == AwakeningListSortTypes.alphabetical:
            awoken_skills = sorted(awoken_skills, key=lambda awo: awo.name_en)
        elif sort_type == AwakeningListSortTypes.numerical:
            awoken_skills = sorted(awoken_skills, key=lambda awo: awo.awoken_skill_id)

        paginated_skills = [awoken_skills[i:i + AwakeningListViewState.MAX_ITEMS_PER_PANE]
                            for i in range(0, len(awoken_skills), AwakeningListViewState.MAX_ITEMS_PER_PANE)]
        return paginated_skills


class AwakeningListView(PadView):
    VIEW_TYPE = 'AwakeningList'

    @classmethod
    def embed_fields(cls, state: AwakeningListViewState) -> List[EmbedField]:
        return [
            EmbedField(
                'Awakenings - by {}'.format(
                    'name' if state.sort_type == AwakeningListSortTypes.alphabetical else 'id number'),
                Box(*[get_awoken_skill_description(
                    awo,
                    show_help=state.qs.showhelp.value,
                    token_map=state.token_map) for awo in state.paginated_skills[state.current_page]]
                    )),
            EmbedField('Page', Box(
                '{} of {}'.format(str(state.current_page + 1), str(len(state.paginated_skills)))
            ))
        ]
