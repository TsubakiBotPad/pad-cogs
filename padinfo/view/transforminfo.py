from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedThumbnail, EmbedMain, EmbedField
from discordmenu.embed.text import Text, BoldText, LabeledText
from discordmenu.embed.view import EmbedView
from tsutils.enums import LsMultiplier
from tsutils.menu.footers import embed_footer_with_state
from tsutils.query_settings import QuerySettings

from padinfo.common.config import UserConfig
from padinfo.common.external_links import puzzledragonx
from padinfo.view.components.base_id_main_view import BaseIdMainView
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.components.view_state_base import ViewStateBase

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.database_context import DbContext


class TransformInfoQueriedProps:
    def __init__(self, acquire_raw, previous_transforms):
        self.acquire_raw = acquire_raw
        self.previous_transforms = previous_transforms


class TransformInfoViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query, color, base_mon, transformed_mon,
                 tfinfo_queried_props: TransformInfoQueriedProps, monster_ids, is_jp_buffed, query_settings,
                 reaction_list):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None)
        self.color = color
        self.base_mon = base_mon
        self.transformed_mon = transformed_mon
        self.acquire_raw = tfinfo_queried_props.acquire_raw
        self.previous_transforms = tfinfo_queried_props.previous_transforms
        self.monster_ids = monster_ids
        self.is_jp_buffed = is_jp_buffed
        self.query_settings: QuerySettings = query_settings
        self.reaction_list = reaction_list

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'query_settings': self.query_settings.serialize(),
            'resolved_monster_ids': self.monster_ids,
            'reaction_list': self.reaction_list
        })
        return ret

    @staticmethod
    async def deserialize(dbcog, user_config: UserConfig, ims: dict):
        raw_query = ims['raw_query']
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        monster_ids = ims['resolved_monster_ids']
        base_mon_id = monster_ids[0]
        transformed_mon_id = monster_ids[1]
        query_settings = QuerySettings.deserialize(ims.get('query_settings'))

        base_mon = dbcog.get_monster(base_mon_id, server=query_settings.server)
        transformed_mon = dbcog.get_monster(transformed_mon_id, server=query_settings.server)

        tfinfo_queried_props = await TransformInfoViewState.do_query(dbcog, transformed_mon)
        reaction_list = ims['reaction_list']
        is_jp_buffed = dbcog.database.graph.monster_is_discrepant(
            base_mon) or dbcog.database.graph.monster_is_discrepant(transformed_mon)

        return TransformInfoViewState(original_author_id, menu_type, raw_query, user_config.color,
                                      base_mon, transformed_mon, tfinfo_queried_props, monster_ids, is_jp_buffed,
                                      query_settings,
                                      reaction_list=reaction_list)

    @staticmethod
    async def do_query(dbcog, transformed_mon) -> TransformInfoQueriedProps:
        db_context = dbcog.database
        db_context: "DbContext"
        acquire_raw = db_context.graph.monster_acquisition(transformed_mon)
        previous_transforms = db_context.graph.get_all_prev_transforms(transformed_mon)
        return TransformInfoQueriedProps(acquire_raw, previous_transforms)


def _get_tf_stat_diff_text(stat, tf_stat):
    return Box(
        Text(str(stat)),
        Text('-> {}'.format(tf_stat)),
        delimiter=' '
    )


def transformat(text: str):
    return '__{}__'.format(text)


class TransformInfoView(BaseIdMainView):
    VIEW_TYPE = 'TransformInfo'

    @classmethod
    def base_info(cls, m: "MonsterModel"):
        return Box(
            Box(
                cls.down_emoji,
                cls.normal_awakenings_row(m) if len(m.awakenings) != 0
                else Box(Text('No Awakenings')),
                delimiter=' '
            ),
            cls.super_awakenings_row(m)
        )

    @classmethod
    def card_info(cls, base_mon: "MonsterModel", transformed_mon: "MonsterModel", acquire_raw):
        rarity = Box(
            LabeledText('Rarity', '{} -> {}'.format(base_mon.rarity, transformed_mon.rarity)),
            Text("" if base_mon.orb_skin_id is None else "(Orb Skin)"),
            delimiter=' '
        )
        cost = LabeledText('Cost', '{} -> {}'.format(base_mon.cost, transformed_mon.cost))
        acquire = BoldText(acquire_raw) if acquire_raw else None

        return Box(rarity, cost, acquire)

    @classmethod
    def stats(cls, base_mon: "MonsterModel", transformed_mon: "MonsterModel"):
        base_hp, base_atk, base_rcv, base_weighted = base_mon.stats()
        tf_hp, tf_atk, tf_rcv, tf_weighed = transformed_mon.stats()
        return Box(
            LabeledText('HP', _get_tf_stat_diff_text(base_hp, tf_hp)),
            LabeledText('ATK', _get_tf_stat_diff_text(base_atk, tf_atk)),
            LabeledText('RCV', _get_tf_stat_diff_text(base_rcv, tf_rcv))
        )

    @classmethod
    def transform_active_header(cls, m: "MonsterModel"):
        active_skill = m.active_skill
        active_cd = '({} cd)'.format(active_skill.turn_min) if active_skill else 'None'
        return Box(
            cls.up_emoji,
            BoldText('Transform Active Skill {}'.format(active_cd)),
            delimiter=' '
        )

    @classmethod
    def base_active_header(cls, m: "MonsterModel"):
        return Box(
            cls.down_emoji,
            BoldText('Base'),
            cls.active_skill_header(m, []),
            delimiter=' '
        )

    @classmethod
    def leader_header(cls, m: "MonsterModel", is_base: bool, lsmultiplier: LsMultiplier, base_mon: "MonsterModel"):
        if is_base:
            emoji = cls.down_emoji
            label = 'Base'
        else:
            emoji = cls.up_emoji
            label = 'Transform'

        return Box(
            emoji,
            BoldText(label),
            cls.leader_skill_header(m, lsmultiplier, base_mon).to_markdown(),
            delimiter=' '
        )

    @classmethod
    def embed(cls, state: TransformInfoViewState):
        base_mon = state.base_mon
        transformed_mon = state.transformed_mon
        lsmultiplier = state.query_settings.lsmultiplier
        fields = [
            EmbedField(
                '/'.join(['{}'.format(t.name) for t in transformed_mon.types]),
                Box(
                    Box(
                        cls.up_emoji,
                        cls.normal_awakenings_row(transformed_mon)
                        if len(transformed_mon.awakenings) != 0 else Box(Text('No Awakenings')),
                        delimiter=' '
                    ),
                    TransformInfoView.base_info(base_mon),
                    cls.killers_row(base_mon, base_mon)
                ),
            ),
            EmbedField(
                BoldText(transformat('Card info')),
                TransformInfoView.card_info(base_mon, transformed_mon, state.acquire_raw),
                inline=True
            ),
            EmbedField(
                BoldText('Stats -> ' + transformat('Transform')),
                TransformInfoView.stats(base_mon, transformed_mon),
                inline=True
            ),
            EmbedField(
                transformat(TransformInfoView.transform_active_header(transformed_mon).to_markdown()),
                Box(
                    Text(transformed_mon.active_skill.desc if transformed_mon.active_skill
                         else 'None'),
                    TransformInfoView.base_active_header(base_mon).to_markdown(),
                    Text(base_mon.active_skill.desc if base_mon.active_skill else 'None')
                )
            ),
            EmbedField(
                transformat(
                    TransformInfoView.leader_header(transformed_mon, False, lsmultiplier, base_mon).to_markdown()),
                Box(
                    Text(transformed_mon.leader_skill.desc if transformed_mon.leader_skill
                         else 'None'),
                    TransformInfoView.leader_header(base_mon, True, lsmultiplier, base_mon).to_markdown(),
                    Text(base_mon.leader_skill.desc if base_mon.leader_skill else 'None')
                )
            )
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
                title=MonsterHeader.fmt_id_header(transformed_mon,
                                                  False,
                                                  state.is_jp_buffed).to_markdown(),
                url=puzzledragonx(transformed_mon)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(transformed_mon)),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields
        )
