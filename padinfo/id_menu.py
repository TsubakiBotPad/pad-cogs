import random
import urllib.parse
from typing import TYPE_CHECKING

import discord
import prettytable
from discord import Color
from redbot.core.utils.chat_formatting import box

from padinfo.common.external_links import puzzledragonx
from padinfo.core.leader_skills import createSingleMultiplierText
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.monster.image import MonsterImage
from padinfo.view.evomats import VoreView
from padinfo.view.evos import EvosView
from padinfo.view.id import IdView
from padinfo.view.leader_skill import LeaderSkillView
from padinfo.view.links import LinksView
from padinfo.view.lookup import LookupView
from padinfo.view.pantheon import PantheonView
from padinfo.view.pic import PicsView

if TYPE_CHECKING:
    from dadguide.database_context import DbContext
    from dadguide.models.monster_model import MonsterModel

INFO_PDX_TEMPLATE = 'http://www.puzzledragonx.com/en/monster.asp?n={}'

YT_SEARCH_TEMPLATE = 'https://www.youtube.com/results?search_query={}'
SKYOZORA_TEMPLATE = 'http://pad.skyozora.com/pets/{}'
ILMINA_TEMPLATE = 'https://ilmina.com/#/CARD/{}'


class IdMenu:
    def __init__(self, ctx, db_context: "DbContext" = None, allowed_emojis: list = None):
        self.ctx = ctx
        self.db_context = db_context
        self.allowed_emojis = allowed_emojis

    async def make_base_embed(self, m: "MonsterModel"):
        header = MonsterHeader.long(m)
        embed = await self.make_custom_embed()
        embed.set_thumbnail(url=MonsterImage.icon(m))
        embed.title = header
        embed.url = puzzledragonx(m)
        embed.set_footer(text='Requester may click the reactions below to switch tabs')
        return embed

    async def get_user_embed_color(self, pdicog):
        color = await pdicog.config.user(self.ctx.author).color()
        if color is None:
            return Color.default()
        elif color == "random":
            return Color(random.randint(0x000000, 0xffffff))
        else:
            return discord.Color(color)

    async def make_id_embed_v2(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        is_transform_base = self.db_context.graph.monster_is_transform_base(m)
        true_evo_type_raw = self.db_context.graph.true_evo_type_by_monster(m).value
        acquire_raw = self.db_context.graph.monster_acquisition(m)
        base_rarity = self.db_context.graph.get_base_monster_by_id(m.monster_no).rarity
        alt_monsters = sorted({*self.db_context.graph.get_alt_monsters_by_id(m.monster_no)},
                              key=lambda x: x.monster_id)
        e = IdView.embed(m, color, is_transform_base, true_evo_type_raw, acquire_raw, base_rarity, alt_monsters)
        return e.to_embed()

    async def make_evo_embed_v2(self, m: "MonsterModel"):
        alt_versions = self.db_context.graph.get_alt_monsters_by_id(m.monster_no)
        gem_versions = list(filter(None, map(self.db_context.graph.evo_gem_monster, alt_versions)))
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        e = EvosView.embed(m, alt_versions, gem_versions, color)
        return e.to_embed()

    def _add_mats_of_list(self, embed, monster_id_list, field_name):
        if not len(monster_id_list):
            return
        field_data = ''
        if len(monster_id_list) > 5:
            field_data = '{} monsters'.format(len(monster_id_list))
        else:
            item_count = min(len(monster_id_list), 5)
            monster_list = [self.db_context.graph.get_monster(m) for m in monster_id_list]
            for ae in sorted(monster_list, key=lambda x: x.monster_no_na, reverse=True)[:item_count]:
                field_data += "{}\n".format(MonsterHeader.long(ae, link=True))
        embed.add_field(name=field_name, value=field_data)

    async def make_evo_mats_embed(self, m: "MonsterModel"):
        mats = self.db_context.graph.evo_mats_by_monster(m)
        usedin = self.db_context.graph.material_of_monsters(m)
        evo_gem = self.db_context.graph.evo_gem_monster(m)
        gemusedin = self.db_context.graph.material_of_monsters(evo_gem) if evo_gem else []
        skillups = [su for su in self.db_context.get_monsters_by_active(m.active_skill.active_skill_id)
                    if self.db_context.graph.monster_is_farmable_evo(su)]
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))

        return VoreView.embed(m, mats, usedin, gemusedin, skillups, color).to_embed()

    async def make_pantheon_embed(self, m: "MonsterModel"):
        full_pantheon = self.db_context.get_monsters_by_series(m.series_id)
        pantheon_list = list(filter(lambda x: self.db_context.graph.monster_is_base(x), full_pantheon))
        if len(pantheon_list) == 0 or len(pantheon_list) > 20:
            return None

        series_name = self.db_context.graph.get_monster(m.monster_no).series.name
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return PantheonView.embed(m, color, pantheon_list, series_name).to_embed()

    async def make_picture_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return PicsView.embed(m, color).to_embed()

    async def make_ls_embed(self, left_m: "MonsterModel", right_m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return LeaderSkillView.embed(left_m, right_m, color).to_embed()

    async def make_lookup_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return LookupView.embed(m, color).to_embed()

    async def make_otherinfo_embed(self, m: "MonsterModel"):
        embed = await self.make_base_embed(m)
        # Clear the thumbnail, takes up too much space
        embed.set_thumbnail(url='')

        body_text = '\n'
        stat_cols = ['', 'HP', 'ATK', 'RCV']
        for plus in (0, 297):
            body_text += '**Stats at +{}:**'.format(plus)
            tbl = prettytable.PrettyTable(stat_cols)
            tbl.hrules = prettytable.NONE
            tbl.vrules = prettytable.NONE
            tbl.align = "l"
            levels = (m.level, 110) if m.limit_mult > 0 else (m.level,)
            for lv in levels:
                for inh in (False, True):
                    hp, atk, rcv, _ = m.stats(lv, plus=plus, inherit=inh)
                    row_name = 'Lv{}'.format(lv)
                    if inh:
                        row_name = '(Inh)'
                    tbl.add_row([row_name.format(plus), hp, atk, rcv])
            body_text += box(tbl.get_string())

        body_text += "\n**JP Name**: {}".format(m.name_ja)
        body_text += "\n[YouTube]({}) | [Skyozora]({}) | [PDX]({}) | [Ilimina]({})".format(
            YT_SEARCH_TEMPLATE.format(urllib.parse.quote(m.name_ja)),
            SKYOZORA_TEMPLATE.format(m.monster_no_jp),
            INFO_PDX_TEMPLATE.format(m.monster_no_jp),
            ILMINA_TEMPLATE.format(m.monster_no_jp))

        if m.history_us:
            body_text += '\n**History:** {}'.format(m.history_us)

        body_text += '\n**Series:** {}'.format(self.db_context.graph.get_monster(m.monster_no).series.name)
        body_text += '\n**Sell MP:** {:,}'.format(m.sell_mp)
        if m.buy_mp is not None:
            body_text += "  **Buy MP:** {:,}".format(m.buy_mp)

        if m.exp < 1000000:
            xp_text = '{:,}'.format(m.exp)
        else:
            xp_text = '{:.1f}'.format(m.exp / 1000000).rstrip('0').rstrip('.') + 'M'
        body_text += '\n**XP to Max:** {}'.format(xp_text)
        body_text += '  **Max Level:**: {}'.format(m.level)

        # weighted stat calculation & display
        hp, atk, rcv, weighted = m.stats()
        body_text += '\n**Weighted stats:** {}'.format(weighted)
        if m.limit_mult > 0:
            lb_hp, lb_atk, lb_rcv, lb_weighted = m.stats(lv=110)
            body_text += ' | LB {} (+{}%)'.format(lb_weighted, m.limit_mult)

        body_text += '\n**Fodder EXP:** {:,}'.format(m.fodder_exp)
        body_text += '\n**Rarity:** {} **Cost:** {}'.format(m.rarity, m.cost)

        embed.description = body_text

        return embed

    async def make_links_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return LinksView.embed(m, color).to_embed()

    async def make_lssingle_embed(self, m: "MonsterModel"):
        multiplier_text = createSingleMultiplierText(m.leader_skill)

        embed = await self.make_custom_embed()
        embed.title = '{}\n\n'.format(multiplier_text)
        description = ''
        description += '\n**{}**\n{}'.format(
            MonsterHeader.short(m, link=True),
            m.leader_skill.desc if m.leader_skill else 'None')
        embed.description = description

        return embed

    async def make_custom_embed(self):
        pdicog = self.ctx.bot.get_cog("PadInfo")
        color = await pdicog.config.user(self.ctx.author).color()
        if color is None:
            return discord.Embed()
        elif color == "random":
            return discord.Embed(color=random.randint(0x000000, 0xffffff))
        else:
            return discord.Embed(color=discord.Color(color))
