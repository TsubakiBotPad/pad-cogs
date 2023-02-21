from typing import Optional, List, Union

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedField, EmbedFooter
from discordmenu.embed.text import BoldText
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.pad_view import PadViewState, PadView
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.links import MonsterImage
from tsutils.tsubaki.monster_header import MonsterHeader


class GlobalStatsViewState(PadViewState):
    VIEW_STATE_TYPE: str = "PADleGlobalStatsView"

    def __init__(self, original_author_id, menu_type, qs: QuerySettings, raw_query: str = "",
                 current_day=0, num_days=0, extra_state=None, reaction_list=None, monster=None, stats=[]):
        super().__init__(original_author_id, menu_type, raw_query, raw_query, qs,
                         extra_state)
        self.reaction_list = reaction_list
        self.current_day = current_day
        self.num_days = num_days
        self.monster = monster
        self.stats = stats

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'current_day': self.current_day,
            'reaction_list': self.reaction_list,
            'num_days': self.num_days,
        })
        return ret

    @staticmethod
    def increment_page(ims):
        if ims['current_day'] < ims['num_days']:
            ims['current_day'] = ims['current_day'] + 1
        else:
            ims['current_day'] = 1

    @staticmethod
    def decrement_page(ims):
        if ims['current_day'] > 1:
            ims['current_day'] = ims['current_day'] - 1
        else:
            ims['current_day'] = ims['num_days']

    @classmethod
    async def deserialize(cls, dbcog, _user_config: UserConfig, padle_cog, ims: dict):  # noqa
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims['reaction_list']
        current_day = ims['current_day']
        num_days = ims['num_days']
        qs = QuerySettings.deserialize(ims.get('qs'))
        daily_scores_list = await padle_cog.config.save_daily_scores()
        cur_day_scores = await padle_cog.config.all_scores()
        if num_days == current_day:
            return GlobalStatsViewState(original_author_id, menu_type, qs, "", current_day=current_day,
                                        num_days=num_days, reaction_list=reaction_list, monster=None,
                                        stats=cur_day_scores)
        else:
            info = daily_scores_list[current_day - 1]
            m = dbcog.get_monster(int(info[0]))
            return GlobalStatsViewState(original_author_id, menu_type, qs, "", current_day=current_day,
                                        num_days=num_days, reaction_list=reaction_list, monster=m,
                                        stats=info[1])


class GlobalStatsView(PadView):
    VIEW_TYPE = 'PADleGlobalStats'

    @classmethod
    def embed_title(cls, state: GlobalStatsViewState) -> Optional[str]:
        return f"PADle #{state.current_day}"

    @classmethod
    def embed_fields(cls, state: GlobalStatsViewState) -> List[EmbedField]:
        giveups = 0
        completes = 0
        average = 0
        for item in state.stats:
            if item == "X":
                giveups += 1
            else:
                completes += 1
                average += int(item)
        if completes == 0:
            description = (f"**Total Wins**: {completes}\n**Total Losses**: {giveups}\n**Win Rate**: 0%\n"
                           "**Average Guess Count**: 0")
        else:
            description = ("**Total Wins**: {}\n**Total Losses**: {}\n**Win Rate**: {:.2%}\n"
                           "**Average Guess Count**: {:.2f}").format(completes, giveups,
                                                                     completes / (completes + giveups),
                                                                     (average / completes))
        return [EmbedField("Stats", Box(description))]

    @classmethod
    def embed_footer(cls, state: GlobalStatsViewState) -> Optional[EmbedFooter]:
        if state.num_days == state.current_day:
            text = f"PADle #{state.current_day}"
        else:
            text = "Day " + str(state.current_day) + "/" + str(state.num_days)
        return embed_footer_with_state(state, text=text)

    @classmethod
    def embed_description(cls, state: GlobalStatsViewState) -> Optional[Union[Box, str]]:
        if state.num_days == state.current_day:
            return None
        return Box(BoldText(MonsterHeader.menu_title(state.monster).to_markdown()))

    @classmethod
    def embed_thumbnail(cls, state: GlobalStatsViewState) -> Optional[EmbedThumbnail]:
        if state.num_days == state.current_day:
            return None
        return EmbedThumbnail(MonsterImage.icon(state.monster.monster_id))
