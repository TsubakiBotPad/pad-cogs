import random
from typing import TYPE_CHECKING

import discord
from discord import Color

from padinfo.core.padinfo_settings import settings
from padinfo.view.id import IdView
from padinfo.view.leader_skill import LeaderSkillSingleView
from padinfo.view.links import LinksView
from padinfo.view.lookup import LookupView
from padinfo.view_state.id import IdViewState

if TYPE_CHECKING:
    from dadguide.database_context import DbContext
    from dadguide.models.monster_model import MonsterModel


class IdMenu:
    def __init__(self, ctx, dgcog=None, allowed_emojis: list = None):
        self.ctx = ctx
        self.dgcog = dgcog
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
        transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters = \
            await IdViewState.query(self.dgcog, m)
        state = IdViewState("", "TODO", "todo", "", color, m, transform_base, true_evo_type_raw, acquire_raw,
                            base_rarity, alt_monsters,
                            use_evo_scroll=settings.checkEvoID(self.ctx.author.id))
        e = IdView.embed(state)
        return e.to_embed()

    async def make_lookup_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return LookupView.embed(m, color).to_embed()

    async def make_links_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return LinksView.embed(m, color).to_embed()

    async def make_lssingle_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return LeaderSkillSingleView.embed(m, color).to_embed()
