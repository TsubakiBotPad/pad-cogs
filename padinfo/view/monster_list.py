from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView

from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view_state.monster_list import MonsterListViewState


def _monster_list(monsters):
    if not len(monsters):
        return []
    return [
        MonsterHeader.short_with_emoji(mon, link=True)
        for mon in sorted(monsters, key=lambda x: int(x.monster_id))
    ]


class MonsterListView:
    @staticmethod
    def embed(state: MonsterListViewState):
        fields = [
            EmbedField('Monster List',
                       Box(*_monster_list(state.monster_list)))
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title='Monster List',
            ),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields)
