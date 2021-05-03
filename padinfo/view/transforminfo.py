from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.text import Text, BoldText, LabeledText
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.config import UserConfig
from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.components.view_state_base import ViewStateBase
from padinfo.view.id import IdView

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel

BASE_EMOJI = '\N{DOWN-POINTING RED TRIANGLE}'
TRANSFORM_EMOJI = '\N{UP-POINTING RED TRIANGLE}'


class TransformInfoViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query, color, base_mon, transformed_mon,
                 acquire_raw, monster_ids, reaction_list):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None)
        self.color = color
        self.base_mon = base_mon
        self.transformed_mon = transformed_mon
        self.acquire_raw = acquire_raw
        self.monster_ids = monster_ids
        self.reaction_list = reaction_list

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'resolved_monster_ids': self.monster_ids,
            'reaction_list': self.reaction_list
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        monster_ids = ims['resolved_monster_ids']
        base_mon_id = monster_ids[0]
        transformed_mon_id = monster_ids[1]

        base_mon = dgcog.get_monster(base_mon_id)
        transformed_mon = dgcog.get_monster(transformed_mon_id)

        acquire_raw = await TransformInfoViewState.query(dgcog, base_mon, transformed_mon)
        reaction_list = ims['reaction_list']

        return TransformInfoViewState(original_author_id, menu_type, raw_query, user_config.color,
                                      base_mon, transformed_mon, acquire_raw, monster_ids,
                                      reaction_list=reaction_list)

    @staticmethod
    async def query(dgcog, base_mon, transformed_mon):
        db_context = dgcog.database
        acquire_raw = db_context.graph.monster_acquisition(transformed_mon)
        return acquire_raw


def _get_tf_stat_diff_text(stat, tf_stat):
    return Box(
        Text(str(stat)),
        Text('-> {}'.format(tf_stat)),
        delimiter=' '
    )


def transformat(text: str):
    return '__{}__'.format(text)


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


def card_info(base_mon: "MonsterModel", transformed_mon: "MonsterModel", acquire_raw):
    rarity = Box(
        LabeledText('Rarity', '{} -> {}'.format(base_mon.rarity, transformed_mon.rarity)),
        Text("" if base_mon.orb_skin_id is None else "(Orb Skin)"),
        delimiter=' '
    )
    cost = LabeledText('Cost', '{} -> {}'.format(base_mon.cost, transformed_mon.cost))
    acquire = BoldText(acquire_raw) if acquire_raw else None

    return Box(rarity, cost, acquire)


def stats(base_mon: "MonsterModel", transformed_mon: "MonsterModel"):
    base_hp, base_atk, base_rcv, base_weighted = base_mon.stats()
    tf_hp, tf_atk, tf_rcv, tf_weighed = transformed_mon.stats()
    return Box(
        LabeledText('HP', _get_tf_stat_diff_text(base_hp, tf_hp)),
        LabeledText('ATK', _get_tf_stat_diff_text(base_atk, tf_atk)),
        LabeledText('RCV', _get_tf_stat_diff_text(base_rcv, tf_rcv))
    )


def transform_active_header(m: "MonsterModel"):
    active_skill = m.active_skill
    active_cd = '({} cd)'.format(active_skill.turn_min) if active_skill else 'None'
    return Box(
        TRANSFORM_EMOJI,
        BoldText('Transform Active Skill {}'.format(active_cd)),
        delimiter=' '
    )


def base_active_header(m: "MonsterModel"):
    return Box(
        BASE_EMOJI,
        BoldText('Base'),
        IdView.active_skill_header(m, m),
        delimiter=' '
    )


def leader_header(m: "MonsterModel", is_base: bool):
    if is_base:
        emoji = BASE_EMOJI
        label = 'Base'
    else:
        emoji = TRANSFORM_EMOJI
        label = 'Transform'
    leader_skill = m.leader_skill

    return Box(
        emoji,
        BoldText(label),
        IdView.leader_skill_header(m).to_markdown(),
        delimiter=' '
    )


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
                    Box(
                        TRANSFORM_EMOJI,
                        IdView.normal_awakenings_row(transformed_mon)
                        if len(transformed_mon.awakenings) != 0 else Box(Text('No Awakenings')),
                        delimiter=' '
                    ),
                    base_info(base_mon),
                    IdView.killers_row(base_mon, base_mon)
                ),
            ),
            EmbedField(
                BoldText(transformat('Card info')),
                card_info(base_mon, transformed_mon, state.acquire_raw),
                inline=True
            ),
            EmbedField(
                BoldText('Stats -> ' + transformat('Transform')),
                stats(base_mon, transformed_mon),
                inline=True
            ),
            EmbedField(
                transformat(transform_active_header(transformed_mon).to_markdown()),
                Box(
                    Text(transformed_mon.active_skill.desc if transformed_mon.active_skill
                         else 'None'),
                    base_active_header(base_mon).to_markdown(),
                    Text(base_mon.active_skill.desc if base_mon.active_skill else 'None')
                )
            ),
            EmbedField(
                transformat(leader_header(transformed_mon, False).to_markdown()),
                Box(
                    Text(transformed_mon.leader_skill.desc if transformed_mon.leader_skill
                         else 'None'),
                    leader_header(base_mon, True).to_markdown(),
                    Text(base_mon.leader_skill.desc if base_mon.leader_skill else 'None')
                )
            )
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.long_v2(transformed_mon).to_markdown(),
                url=puzzledragonx(transformed_mon)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(transformed_mon)),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
