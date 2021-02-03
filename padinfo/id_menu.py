import random
from typing import TYPE_CHECKING

import discord
from discord import Color

from padinfo.core.id import get_monster_misc_info
from padinfo.view.evos import EvosView
from padinfo.view.id import IdView
from padinfo.view.leader_skill import LeaderSkillView, LeaderSkillSingleView
from padinfo.view.links import LinksView
from padinfo.view.lookup import LookupView
from padinfo.view.materials import MaterialView
from padinfo.view.otherinfo import OtherInfoView
from padinfo.view.pantheon import PantheonView
from padinfo.view.pic import PicsView
from padinfo.view_state.id import IdViewState

if TYPE_CHECKING:
    from dadguide.database_context import DbContext
    from dadguide.models.monster_model import MonsterModel


class IdMenu:
    def __init__(self, ctx, db_context: "DbContext" = None, allowed_emojis: list = None):
        self.ctx = ctx
        self.db_context = db_context
        self.allowed_emojis = allowed_emojis

    async def get_user_embed_color(self, pdicog):
        color = await pdicog.config.user(self.ctx.author).color()
        if color is None:
            return Color.default()
        elif color == "random":
            return Color(random.randint(0x000000, 0xffffff))
        else:
            return discord.Color(color)

    async def make_id_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        acquire_raw, alt_monsters, base_rarity, transform_base, true_evo_type_raw = \
            await get_monster_misc_info(self.db_context, m)
        state = IdViewState("", "TODO", "todo", "", m, color, transform_base, true_evo_type_raw, acquire_raw,
                            base_rarity, alt_monsters)
        e = IdView.embed(state)
        return e.to_embed()

    async def make_evo_embed(self, m: "MonsterModel"):
        alt_versions = self.db_context.graph.get_alt_monsters_by_id(m.monster_no)
        gem_versions = list(filter(None, map(self.db_context.graph.evo_gem_monster, alt_versions)))
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        e = EvosView.embed(m, alt_versions, gem_versions, color)
        return e.to_embed()

    async def make_evo_mats_embed(self, m: "MonsterModel"):
        mats = self.db_context.graph.evo_mats_by_monster(m)
        usedin = self.db_context.graph.material_of_monsters(m)
        evo_gem = self.db_context.graph.evo_gem_monster(m)
        gemid = str(evo_gem.monster_no_na) if evo_gem else None
        gemusedin = self.db_context.graph.material_of_monsters(evo_gem) if evo_gem else []
        skillups = []
        skillup_evo_count = 0

        if m.active_skill:
            sums = [m for m in self.db_context.get_monsters_by_active(m.active_skill.active_skill_id)
                    if self.db_context.graph.monster_is_farmable_evo(m)]
            sugs = [self.db_context.graph.evo_gem_monster(su) for su in sums]
            vsums = []
            for su in sums:
                if not any(susu in vsums for susu in self.db_context.graph.get_alt_monsters(su)):
                    vsums.append(su)
            skillups = [su for su in vsums
                        if self.db_context.graph.monster_is_farmable_evo(su) and
                        self.db_context.graph.get_base_id(su) != self.db_context.graph.get_base_id(m) and
                        su not in sugs] if m.active_skill else []
            skillup_evo_count = len(sums) - len(vsums)

        if not any([mats, usedin, gemusedin, skillups and not m.stackable]):
            return None
        link = "https://ilmina.com/#/SKILL/{}".format(m.active_skill.active_skill_id) if m.active_skill else None
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return MaterialView.embed(m, color, mats, usedin, gemid, gemusedin, skillups, skillup_evo_count,
                                  link).to_embed()

    async def make_pantheon_embed(self, m: "MonsterModel"):
        full_pantheon = self.db_context.get_monsters_by_series(m.series_id)
        pantheon_list = list(filter(lambda x: self.db_context.graph.monster_is_base(x), full_pantheon))
        if len(pantheon_list) == 0 or len(pantheon_list) > 20:
            return None

        series_name = m.series.name_en
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return PantheonView.embed(m, color, pantheon_list, series_name).to_embed()

    async def make_picture_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return PicsView.embed(m, color).to_embed()

    async def make_ls_embed(self, left_m: "MonsterModel", right_m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        embed = LeaderSkillView.embed(left_m, right_m, color)
        return embed.to_embed()

    async def make_lookup_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return LookupView.embed(m, color).to_embed()

    async def make_otherinfo_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return OtherInfoView.embed(m, color).to_embed()

    async def make_links_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return LinksView.embed(m, color).to_embed()

    async def make_lssingle_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return LeaderSkillSingleView.embed(m, color).to_embed()
