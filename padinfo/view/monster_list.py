from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from tsutils import char_to_emoji

from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view_state.monster_list import MonsterListViewState


def _monster_list(monsters):
    if not len(monsters):
        return []
    return [
        MonsterHeader.short_with_emoji(mon, link=True, prefix=char_to_emoji(i))
        for i, mon in enumerate(monsters)
    ]


class MonsterListView:
    @staticmethod
    def embed(state: MonsterListViewState):
        fields = [
            EmbedField(state.title,
                       Box(*_monster_list(state.monster_list)))
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
            ),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields)
