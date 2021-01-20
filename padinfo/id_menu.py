import random
import urllib.parse
from typing import TYPE_CHECKING

import discord
import prettytable
from discord import Color
from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain
from discordmenu.embed.menu import EmbedView
from discordmenu.embed.text import Text, BoldText
from redbot.core.utils.chat_formatting import box

from padinfo.common.emoji_map import awakening_restricted_latent_emoji
from padinfo.view.components.monster.header import MonsterHeader
from .common.padx import monster_url
from .leader_skills import createMultiplierText
from .leader_skills import createSingleMultiplierText
from .view.components.monster.image import MonsterImage
from .view.evos import EvosView
from .view.id import IdView
from .view.leader_skill import LeaderSkillView
from .view.lookup import LookupView

if TYPE_CHECKING:
    from dadguide.database_context import DbContext
    from dadguide.models.monster_model import MonsterModel

INFO_PDX_TEMPLATE = 'http://www.puzzledragonx.com/en/monster.asp?n={}'

MEDIA_PATH = 'https://d1kpnpud0qoyxf.cloudfront.net/media/'
RPAD_PIC_TEMPLATE = MEDIA_PATH + 'portraits/{0:05d}.png?cachebuster=2'
VIDEO_TEMPLATE = MEDIA_PATH + 'animated_portraits/{0:05d}.mp4'
GIF_TEMPLATE = MEDIA_PATH + 'animated_portraits/{0:05d}.gif'
ORB_SKIN_TEMPLATE = MEDIA_PATH + 'orb_skins/jp/{0:03d}.png'
ORB_SKIN_CB_TEMPLATE = MEDIA_PATH + 'orb_skins/jp/{0:03d}cb.png'

YT_SEARCH_TEMPLATE = 'https://www.youtube.com/results?search_query={}'
SKYOZORA_TEMPLATE = 'http://pad.skyozora.com/pets/{}'
ILMINA_TEMPLATE = 'https://ilmina.com/#/CARD/{}'


def get_pic_url(m: "MonsterModel"):
    return RPAD_PIC_TEMPLATE.format(m.monster_id)


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
        embed.url = monster_url(m)
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
        acquire_raw = self._monster_acquisition_string(m)
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
        embed = await self.make_base_embed(m)

        mats_for_evo = self.db_context.graph.evo_mats_by_monster(m)

        field_name = 'Evo materials'
        field_data = ''
        if len(mats_for_evo) > 0:
            for ae in mats_for_evo:
                field_data += "{}\n".format(MonsterHeader.long(ae, link=True))
        else:
            field_data = 'None'
        embed.add_field(name=field_name, value=field_data)

        self._add_mats_of_list(embed, self.db_context.graph.material_of_ids(m), 'Material for')
        evo_gem = self.db_context.graph.evo_gem_monster(m)
        if not evo_gem:
            return embed
        self._add_mats_of_list(embed, self.db_context.graph.material_of_ids(evo_gem), "Evo gem is mat for")
        return embed

    async def make_pantheon_embed(self, m: "MonsterModel"):
        full_pantheon = self.db_context.get_monsters_by_series(m.series_id)
        pantheon_list = list(filter(lambda x: self.db_context.graph.monster_is_base(x), full_pantheon))
        if len(pantheon_list) == 0 or len(pantheon_list) > 20:
            return None

        embed = await self.make_base_embed(m)

        field_name = 'Pantheon: ' + self.db_context.graph.get_monster(m.monster_no).series.name
        field_data = ''
        for monster in sorted(pantheon_list, key=lambda x: x.monster_no_na):
            field_data += '\n' + MonsterHeader.short(monster, link=True)
        embed.add_field(name=field_name, value=field_data)

        return embed

    async def make_skillups_embed(self, m: "MonsterModel"):
        if m.active_skill is None:
            return None
        possible_skillups_list = self.db_context.get_monsters_by_active(m.active_skill.active_skill_id)
        skillups_list = list(filter(
            lambda x: self.db_context.graph.monster_is_farmable_evo(x), possible_skillups_list))

        if len(skillups_list) == 0:
            return None

        embed = await self.make_base_embed(m)

        field_name = 'Skillups'
        field_data = ''

        # Prevent huge skillup lists
        if len(skillups_list) > 8:
            field_data = '({} skillups omitted)'.format(len(skillups_list) - 8)
            skillups_list = skillups_list[0:8]

        for monster in sorted(skillups_list, key=lambda x: x.monster_no_na):
            field_data += '\n' + MonsterHeader.short(monster, link=True)

        if len(field_data.strip()):
            embed.add_field(name=field_name, value=field_data)

        return embed

    async def make_picture_embed(self, m: "MonsterModel", animated=False):
        embed = await self.make_base_embed(m)
        url = get_pic_url(m)
        embed.set_image(url=url)
        # Clear the thumbnail, don't need it on pic
        embed.set_thumbnail(url='')
        extra_links = []
        if animated:
            extra_links.append('Animation: {} -- {}'.format(self.monster_video_url(m), self.monster_gif_url(m)))
        if m.orb_skin_id is not None:
            extra_links.append(
                'Orb Skin: {} -- {}'.format(self.monster_orb_skin_url(m), self.monster_orb_skin_cb_url(m)))
        if len(extra_links) > 0:
            embed.add_field(name='Extra Links', value='\n'.join(extra_links))

        return embed

    @staticmethod
    def monster_video_url(m: "MonsterModel", link_text='(MP4)'):
        return '[{}]({})'.format(link_text, VIDEO_TEMPLATE.format(m.monster_no_jp))

    @staticmethod
    def monster_gif_url(m: "MonsterModel", link_text='(GIF)'):
        return '[{}]({})'.format(link_text, GIF_TEMPLATE.format(m.monster_no_jp))

    @staticmethod
    def monster_orb_skin_url(m: "MonsterModel", link_text='Regular'):
        return '[{}]({})'.format(link_text, ORB_SKIN_TEMPLATE.format(m.orb_skin_id))

    @staticmethod
    def monster_orb_skin_cb_url(m: "MonsterModel", link_text='Color Blind'):
        return '[{}]({})'.format(link_text, ORB_SKIN_CB_TEMPLATE.format(m.orb_skin_id))

    async def make_ls_embed(self, left_m: "MonsterModel", right_m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return LeaderSkillView.embed(left_m, right_m, color).to_embed()

    async def make_lookup_embed(self, m: "MonsterModel"):
        color = await self.get_user_embed_color(self.ctx.bot.get_cog("PadInfo"))
        return LookupView.embed(m, color).to_embed()

    def _monster_acquisition_string(self, m: "MonsterModel"):
        acquire_text = None
        if self.db_context.graph.monster_is_farmable(m) and not self.db_context.graph.monster_is_mp_evo(m):
            # Some MP shop monsters 'drop' in PADR
            acquire_text = 'Farmable'
        elif self.db_context.graph.monster_is_farmable_evo(m) and not self.db_context.graph.monster_is_mp_evo(m):
            acquire_text = 'Farmable Evo'
        elif m.in_pem:
            acquire_text = 'In PEM'
        elif self.db_context.graph.monster_is_pem_evo(m):
            acquire_text = 'PEM Evo'
        elif m.in_rem:
            acquire_text = 'In REM'
        elif self.db_context.graph.monster_is_rem_evo(m):
            acquire_text = 'REM Evo'
        elif m.in_mpshop:
            acquire_text = 'MP Shop'
        elif self.db_context.graph.monster_is_mp_evo(m):
            acquire_text = 'MP Shop Evo'
        return acquire_text

    def get_awakening_restricted_latents_text(self, m: "MonsterModel"):
        """Not currently in use, but potentially could be in the future
        if more ARLatents are added later
        """
        if not m.awakening_restricted_latents:
            return ''
        return ' ' + ' '.join([awakening_restricted_latent_emoji(x) for x in m.awakening_restricted_latents])

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
        embed = await self.make_base_embed(m)
        embed.description = "\n[YouTube]({}) | [Skyozora]({}) | [PDX]({}) | [Ilimina]({})".format(
            YT_SEARCH_TEMPLATE.format(urllib.parse.quote(m.name_ja)),
            SKYOZORA_TEMPLATE.format(m.monster_no_jp),
            INFO_PDX_TEMPLATE.format(m.monster_no_jp),
            ILMINA_TEMPLATE.format(m.monster_no_jp))
        embed.set_footer(text='')
        return embed

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
