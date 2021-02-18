from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.text import Text
from discordmenu.embed.view import EmbedView

from padinfo.common.config import UserConfig
from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.id import IdView
from padinfo.view_state.base import ViewStateBase

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

BASE_EMOJI = '\N{DOWN-POINTING RED TRIANGLE}'


def base_info(m: "MonsterModel"):
    return Box(
        Box(
            BASE_EMOJI,
            IdView.normal_awakenings_row(m) if len(m.awakenings) != 0
            else Box(Text('No Awakenings')),
            delimiter=' '
        ),
        IdView.super_awakenings_row(m)
    )


def base_skill(m: "MonsterModel"):
    active_skill = m.active_skill
    return (" (" + BASE_EMOJI + " "
            + "{} -> {})".format(active_skill.turn_max, active_skill.turn_min) if active_skill
            else 'None')


class TransformInfoViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query, color, base_mon, transformed_mon,
                 base_rarity, acquire_raw, true_evo_type_raw):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None)
        self.color = color
        self.base_mon = base_mon
        self.transformed_mon = transformed_mon
        self.base_rarity = base_rarity
        self.acquire_raw = acquire_raw
        self.true_evo_type_raw = true_evo_type_raw

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'b_resolved_monster_id': self.base_mon.monster_id,
            't_resolved_monster_id': self.transformed_mon.monster_id
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        base_mon_id = ims['b_resolved_monster_id']
        transformed_mon_id = ims['t_resolved_monster_id']

        base_mon = dgcog.get_monster(base_mon_id)
        transformed_mon = dgcog.get_monster(transformed_mon_id)

        acquire_raw, base_rarity, true_evo_type_raw = \
            await TransformInfoViewState.query(dgcog, base_mon, transformed_mon)

        return TransformInfoViewState(original_author_id, menu_type, raw_query, user_config.color,
                                      base_mon, transformed_mon, base_rarity, acquire_raw,
                                      true_evo_type_raw)

    @staticmethod
    async def query(dgcog, base_mon, transformed_mon):
        db_context = dgcog.database
        acquire_raw = db_context.graph.monster_acquisition(transformed_mon)
        base_rarity = db_context.graph.get_base_monster_by_id(transformed_mon.monster_no).rarity
        true_evo_type_raw = db_context.graph.true_evo_type_by_monster(transformed_mon).value
        return acquire_raw, base_rarity, true_evo_type_raw


class TransformInfoView:
    VIEW_TYPE = 'TransformInfo'

    @staticmethod
    def embed(state: TransformInfoViewState):
        base_mon = state.base_mon
        transformed_mon = state.transformed_mon

        fields = [
            EmbedField(
                '/'.join(['{}'.format(t.name) for t in transformed_mon.types]),
                Box(
                    IdView.normal_awakenings_row(transformed_mon)
                    if len(transformed_mon.awakenings) != 0 else Box(Text('No Awakenings')),
                    base_info(base_mon),
                    IdView.killers_row(transformed_mon, base_mon)
                ),
            ),
            EmbedField(
                'Card info',
                IdView.misc_info(transformed_mon, state.true_evo_type_raw, state.acquire_raw,
                                 state.base_rarity),
                inline=True
            ),
            EmbedField(
                IdView.stats_header(transformed_mon).to_markdown(),
                IdView.stats(transformed_mon),
                inline=True
            ),
            EmbedField(
                IdView.active_skill_header(transformed_mon, base_mon).to_markdown(),
                Text(transformed_mon.active_skill.desc if transformed_mon.active_skill else 'None')
            ),
            EmbedField(
                IdView.leader_skill_header(transformed_mon).to_markdown(),
                Text(transformed_mon.leader_skill.desc if transformed_mon.leader_skill else 'None')
            )
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_v2(transformed_mon).to_markdown(),
                url=puzzledragonx(transformed_mon)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(transformed_mon)),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields
        )
