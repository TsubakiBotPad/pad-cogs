from discordmenu.embed.components import EmbedMain, EmbedThumbnail
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.view_state_base import ViewStateBase
from tsutils.tsubaki.links import MonsterImage
from tsutils.tsubaki.monster_header import MonsterHeader


class GlobalStatsViewState(ViewStateBase):
    VIEW_STATE_TYPE: str = "GlobalStatsView"

    def __init__(self, original_author_id, menu_type, raw_query="", current_day=0, num_days=0,
                 extra_state=None, reaction_list=None, monster=None, stats=[]):
        super().__init__(original_author_id, menu_type, raw_query,
                         extra_state=extra_state)
        self.reaction_list = reaction_list
        self.current_day = current_day
        self.num_days = num_days
        self.monster = monster
        self.stats = stats

    def get_pages_footer(self):
        return "Day " + str(self.current_day) + "/" + str(self.num_days)

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'current_day': self.current_day,
            'reaction_list': self.reaction_list,
            'num_days': self.num_days
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, _user_config: UserConfig, daily_scores_list, cur_day_scores, ims: dict):
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims['reaction_list']
        current_day = ims['current_day']
        num_days = ims['num_days']
        if num_days == current_day:
            return GlobalStatsViewState(original_author_id, menu_type, "", current_day=current_day,
                                        num_days=num_days, reaction_list=reaction_list, monster=None,
                                        stats=cur_day_scores)
        else:
            info = daily_scores_list[current_day - 1]
            m = dbcog.get_monster(int(info[0]))
            return GlobalStatsViewState(original_author_id, menu_type, "", current_day=current_day,
                                        num_days=num_days, reaction_list=reaction_list, monster=m,
                                        stats=info[1])


class GlobalStatsView:
    VIEW_TYPE = 'GlobalStats'

    @staticmethod
    def embed(state: GlobalStatsViewState):

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

        if state.num_days == state.current_day:
            return EmbedView(
                EmbedMain(
                    title=f"**PADle #{state.current_day} Stats**",
                    description=description
                ),
                embed_footer=embed_footer_with_state(state, text=state.get_pages_footer()))
        else:
            return EmbedView(
                EmbedMain(
                    title=f"**PADle #{state.current_day} Stats**",
                    description="**" + MonsterHeader.menu_title(state.monster).to_markdown() + "**\n" + description,
                ),
                embed_footer=embed_footer_with_state(state, text=state.get_pages_footer()),
                embed_thumbnail=EmbedThumbnail(MonsterImage.icon(state.monster.monster_id)))
