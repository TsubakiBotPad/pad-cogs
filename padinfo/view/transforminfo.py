from typing import TYPE_CHECKING

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedField, EmbedMain, EmbedThumbnail
from discordmenu.embed.text import BoldText, LabeledText, Text
from discordmenu.embed.view import EmbedView
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.view_state_base import ViewStateBase
from tsutils.query_settings.enums import LsMultiplier
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.custom_emoji import get_emoji
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from padinfo.view.components.base_id_main_view import BaseIdMainView

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.database_context import DbContext


class TransformInfoQueriedProps:
    def __init__(self, acquire_raw, previous_transforms, awoken_skill_map):
        self.acquire_raw = acquire_raw
        self.previous_transforms = previous_transforms
        self.awoken_skill_map = awoken_skill_map


class TransformInfoViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query, base_mon, transformed_mon,
                 tfinfo_queried_props: TransformInfoQueriedProps, monster_ids, is_jp_buffed, query_settings,
                 reaction_list):
        super().__init__(original_author_id, menu_type, raw_query, extra_state=None)
        self.base_mon = base_mon
        self.transformed_mon = transformed_mon
        self.acquire_raw = tfinfo_queried_props.acquire_raw
        self.previous_transforms = tfinfo_queried_props.previous_transforms
        self.awoken_skill_map = tfinfo_queried_props.awoken_skill_map
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

        return TransformInfoViewState(original_author_id, menu_type, raw_query,
                                      base_mon, transformed_mon, tfinfo_queried_props, monster_ids, is_jp_buffed,
                                      query_settings,
                                      reaction_list=reaction_list)

    @staticmethod
    async def do_query(dbcog, transformed_mon) -> TransformInfoQueriedProps:
        db_context = dbcog.database
        db_context: "DbContext"
        acquire_raw = db_context.graph.monster_acquisition(transformed_mon)
        previous_transforms = db_context.graph.get_all_prev_transforms(transformed_mon)
        awoken_skill_map = db_context.awoken_skill_map
        return TransformInfoQueriedProps(acquire_raw, previous_transforms, awoken_skill_map)


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
                get_emoji(cls.down_emoji_name),
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
            Text("" if base_mon.bgm_id is None else "(BGM)"),
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
        active_cd = '({} cd)'.format(active_skill.cooldown_turns_min) if active_skill else 'None'
        return Box(
            get_emoji(cls.up_emoji_name),
            BoldText('Transform AS {}'.format(active_cd)),
            delimiter=' '
        )

    @classmethod
    def base_active_header(cls, m: "MonsterModel"):
        return Box(
            get_emoji(cls.down_emoji_name),
            BoldText('Base'),
            cls.active_skill_header(m, []),
            delimiter=' '
        )

    @classmethod
    def leader_header(cls, m: "MonsterModel", is_base: bool, lsmultiplier: LsMultiplier, base_mon: "MonsterModel"):
        if is_base:
            emoji = get_emoji(cls.down_emoji_name)
            label = 'Base'
        else:
            emoji = get_emoji(cls.up_emoji_name)
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
        qs = state.query_settings
        transformed_mon = state.transformed_mon
        lsmultiplier = qs.lsmultiplier
        fields = [
            EmbedField(
                '/'.join(['{}'.format(t.name) for t in transformed_mon.types]),
                Box(
                    Box(
                        get_emoji(cls.up_emoji_name),
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
                    Text(cls.active_skill_text(
                        transformed_mon.active_skill, state.awoken_skill_map, qs.skilldisplay)),
                    TransformInfoView.base_active_header(base_mon).to_markdown(),
                    Text(cls.active_skill_text(
                        base_mon.active_skill, state.awoken_skill_map, qs.skilldisplay))
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
                color=qs.embedcolor,
                title=MonsterHeader.menu_title(transformed_mon,
                                               is_tsubaki=False,
                                               is_jp_buffed=state.is_jp_buffed).to_markdown(),
                url=MonsterLink.header_link(transformed_mon, qs)
            ),
            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(transformed_mon.monster_id)),
            embed_footer=embed_footer_with_state(state, qs=qs),
            embed_fields=fields
        )
