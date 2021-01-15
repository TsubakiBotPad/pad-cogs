import asyncio
from datetime import datetime
import json
import logging
import os
import random
import re
import urllib.parse
from collections import OrderedDict, defaultdict
from enum import Enum
from io import BytesIO
from typing import TYPE_CHECKING

import discord
import tsutils
from discordmenu.emoji_cache import emoji_cache
from redbot.core import checks, commands, data_manager, Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, inline, pagify, text_to_file
from tabulate import tabulate
from tsutils import CogSettings, EmojiUpdater, Menu, char_to_emoji, rmdiacritics, safe_read_json, is_donor

from .button_info import button_info
from .find_monster import find_monster, SERIES_TYPE_PRIORITY as series_priority
from .id_menu import IdMenu
from .view.components.monster.header import MonsterHeader

if TYPE_CHECKING:
    from dadguide.database_context import DbContext
    from dadguide.models.monster_model import MonsterModel
    from dadguide.old_monster_index import NamedMonster

logger = logging.getLogger('red.padbot-cogs.padinfo')

EMBED_NOT_GENERATED = -1

IDGUIDE = "https://github.com/TsubakiBotPad/pad-cogs/wiki/%5Eid-user-guide"

class ServerFilter(Enum):
    any = 0
    na = 1
    jp = 2


def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='padinfo')), file_name)


COLORS = {
    **{c: getattr(discord.Colour, c)().value for c in discord.Colour.__dict__ if
       isinstance(discord.Colour.__dict__[c], classmethod) and
       discord.Colour.__dict__[c].__func__.__code__.co_argcount == 1 and
       isinstance(getattr(discord.Colour, c)(), discord.Colour)},
    'pink': 0xffa1dd,

    # Special
    'random': 'random',
    'clear': 0,
}


class IdEmojiUpdater(EmojiUpdater):
    def __init__(self, ctx, emoji_to_embed, m: "MonsterModel" = None, pad_info=None, selected_emoji=None, bot=None,
                 db_context: "DbContext" = None, **kwargs):
        super().__init__(emoji_to_embed, **kwargs)
        self.ctx = ctx
        self.emoji_dict = emoji_to_embed
        self.m = m
        self.pad_info = pad_info
        self.selected_emoji = selected_emoji
        self.bot = bot
        self.db_context = db_context

        self.pad_info.settings.log_emoji("start_" + selected_emoji)

    async def on_update(self, ctx, selected_emoji):
        evo_id = self.pad_info.settings.checkEvoID(ctx.author.id)
        self.pad_info.settings.log_emoji(selected_emoji)
        if evo_id:
            evos = sorted({*self.db_context.graph.get_alt_ids_by_id(self.m.monster_id)})
            index = evos.index(self.m.monster_id)
            if selected_emoji == self.pad_info.previous_monster_emoji:
                new_id = evos[index - 1]
            elif selected_emoji == self.pad_info.next_monster_emoji:
                if index == len(evos) - 1:
                    new_id = evos[0]
                else:
                    new_id = evos[index + 1]
            else:
                self.selected_emoji = selected_emoji
                return True
            if new_id == self.m.monster_id:
                return False
            self.m = self.db_context.graph.get_monster(new_id)
        else:
            if selected_emoji == self.pad_info.previous_monster_emoji:
                prev_monster = self.db_context.graph.numeric_prev_monster(self.m)
                if prev_monster is None:
                    return False
                self.m = prev_monster
            elif selected_emoji == self.pad_info.next_monster_emoji:
                next_monster = self.db_context.graph.numeric_next_monster(self.m)
                if next_monster is None:
                    return False
                self.m = next_monster
            else:
                self.selected_emoji = selected_emoji
                return True

        self.emoji_dict = await self.pad_info.get_id_emoji_options(self.ctx,
                                                                   m=self.m, scroll=sorted(
                {*self.db_context.graph.get_alt_ids_by_id(self.m.monster_id)}) if evo_id else [], menu_type=1)
        return True


class ScrollEmojiUpdater(EmojiUpdater):
    def __init__(self, ctx, emoji_to_embed, m: "MonsterModel" = None, ms: "list[int]" = None, selected_emoji=None,
                 pad_info=None, bot=None, **kwargs):
        super().__init__(emoji_to_embed, **kwargs)
        self.ctx = ctx
        self.emoji_dict = emoji_to_embed
        self.m = m
        self.ms = ms
        self.pad_info = pad_info
        self.selected_emoji = selected_emoji
        self.bot = bot

    async def on_update(self, ctx, selected_emoji):
        index = self.ms.index(self.m)

        if selected_emoji == self.pad_info.first_monster_emoji:
            self.m = self.ms[0]
        elif selected_emoji == self.pad_info.previous_monster_emoji:
            self.m = self.ms[index - 1]
        elif selected_emoji == self.pad_info.next_monster_emoji:
            if index == len(self.ms) - 1:
                self.m = self.ms[0]
            else:
                self.m = self.ms[index + 1]
        elif selected_emoji == self.pad_info.last_monster_emoji:
            self.m = self.ms[-1]
        else:
            self.selected_emoji = selected_emoji
            return True

        self.emoji_dict = await self.pad_info.get_id_emoji_options(self.ctx, m=self.m, scroll=self.ms)
        return True


class PadInfo(commands.Cog):
    """Info for PAD Cards"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.settings = PadInfoSettings("padinfo")

        self.index_all = None
        self.index_na = None
        self.index_jp = None
        self.index_lock = asyncio.Lock()

        self.menu = Menu(bot)

        # These emojis are the keys into the idmenu submenus
        self.id_emoji = '\N{HOUSE BUILDING}'
        self.evo_emoji = char_to_emoji('e')
        self.mats_emoji = char_to_emoji('m')
        self.ls_emoji = '\N{HOUSE BUILDING}'
        self.left_emoji = char_to_emoji('l')
        self.right_emoji = char_to_emoji('r')
        self.pantheon_emoji = '\N{CLASSICAL BUILDING}'
        self.skillups_emoji = '\N{MEAT ON BONE}'
        self.pic_emoji = '\N{FRAME WITH PICTURE}'
        self.other_info_emoji = '\N{SCROLL}'
        self.first_monster_emoji = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
        self.previous_monster_emoji = '\N{BLACK LEFT-POINTING TRIANGLE}'
        self.next_monster_emoji = '\N{BLACK RIGHT-POINTING TRIANGLE}'
        self.last_monster_emoji = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'
        self.remove_emoji = self.menu.emoji['no']

        self.historic_lookups_file_path = _data_file('historic_lookups.json')
        self.historic_lookups = safe_read_json(self.historic_lookups_file_path)

        self.historic_lookups_file_path_id2 = _data_file('historic_lookups_id2.json')
        self.historic_lookups_id2 = safe_read_json(self.historic_lookups_file_path_id2)

        self.historic_lookups_file_path_id3 = _data_file('historic_lookups_id3.json')
        self.historic_lookups_id3 = safe_read_json(self.historic_lookups_file_path_id3)

        self.config = Config.get_conf(self, identifier=9401770)
        self.config.register_user(survey_mode=0, color=None, beta_id3=False)
        self.config.register_global(sometimes_perc=20, good=0, bad=0, do_survey=False, test_suite={})

        emoji_cache.set_guild_ids([g.id for g in self.bot.guilds])
        emoji_cache.refresh_from_discord_bot(self.bot)

    def cog_unload(self):
        # Manually nulling out database because the GC for cogs seems to be pretty shitty
        self.index_all = None
        self.index_na = None
        self.index_jp = None
        self.historic_lookups = {}
        self.historic_lookups_id2 = {}
        self.historic_lookups_id3 = {}

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    async def reload_nicknames(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('PadInfo'):
            wait_time = 60 * 60 * 1
            try:
                await self.refresh_index()
            except Exception as ex:
                wait_time = 5
                logger.exception("reload padinfo loop caught exception " + str(ex))

            await asyncio.sleep(wait_time)

    async def refresh_index(self):
        """Refresh the monster indexes."""
        dg_cog = self.bot.get_cog('Dadguide')
        if not dg_cog:
            logger.warning("Cog 'Dadguide' not loaded")
            return
        logger.info('Waiting until DG is ready')
        await dg_cog.wait_until_ready()

        async with self.index_lock:
            logger.debug('Loading ALL index')
            self.index_all = await dg_cog.create_index()

            logger.debug('Loading NA index')
            self.index_na = await dg_cog.create_index(lambda m: m.on_na)

            logger.debug('Loading JP index')
            self.index_jp = await dg_cog.create_index(lambda m: m.on_jp)

        logger.info('Done refreshing indexes')

    def get_monster(self, monster_id: int):
        dg_cog = self.bot.get_cog('Dadguide')
        return dg_cog.get_monster(monster_id)

    @commands.command()
    async def jpname(self, ctx, *, query: str):
        """Show the Japanese name of a monster"""
        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        if m is not None:
            await ctx.send(MonsterHeader.short(m))
            await ctx.send(box(m.name_ja))
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command(name="id", aliases=["iD", "Id", "ID"])
    @checks.bot_has_permissions(embed_links=True)
    async def _id(self, ctx, *, query: str):
        """Monster info (main tab)"""
        if await self.config.user(ctx.author).beta_id3():
            await self._do_id3(ctx, query)
        else:
            await self._do_id(ctx, query)

    @commands.command(aliases=["idold", "oldid"])
    @checks.bot_has_permissions(embed_links=True)
    async def id1(self, ctx, *, query):
        """Do a search via id1"""
        await self._do_id(ctx, query)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def idna(self, ctx, *, query: str):
        """Monster info (limited to NA monsters ONLY)"""
        await self._do_id(ctx, query, server_filter=ServerFilter.na)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def idjp(self, ctx, *, query: str):
        """Monster info (limited to JP monsters ONLY)"""
        await self._do_id(ctx, query, server_filter=ServerFilter.jp)

    async def _do_id(self, ctx, query: str, server_filter=ServerFilter.any):
        m, err, debug_info = await self.findMonster1(query, server_filter=server_filter)

        if m is not None:
            await self._do_idmenu(ctx, m, self.id_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    async def send_survey_after(self, ctx, query, result_monster):
        sm = await self.config.user(ctx.author).survey_mode()
        sms = [1, await self.config.sometimes_perc() / 100, 0][sm]
        if random.random() < sms:
            m1, _, _ = await self.findMonster1(query)
            id1res = f"{m1.name_en} ({m1.monster_id})" if m1 else "None"
            id3res = f"{result_monster.name_en} ({result_monster.monster_id})" if result_monster else "None"
            params = urllib.parse.urlencode(
                {'usp': 'pp_url', 'entry.154088017': query, 'entry.173096863': id3res, 'entry.1016180044': id1res})
            url = "https://docs.google.com/forms/d/e/1FAIpQLSeA2EBYiZTOYfGLNtTHqYdL6gMZrfurFZonZ5dRQa3XPHP9yw/viewform?" + params
            await asyncio.sleep(1)
            userres = await tsutils.confirm_message(ctx, "Was this the monster you were looking for?",
                                                    yemoji=char_to_emoji('y'), nemoji=char_to_emoji('n'))
            if userres is True:
                await self.config.good.set(await self.config.good() + 1)
            elif userres is False:
                await self.config.bad.set(await self.config.bad() + 1)
                m = await ctx.send(f"Oh no!  You can help the Tsubaki team give better results"
                                   f" by filling out this survey!\nPRO TIP: Use `{ctx.prefix}idset"
                                   f" survey` to adjust how often this shows.\n\n<{url}>")
                await asyncio.sleep(15)
                await m.delete()

    @commands.group()
    async def idsurvey(self, ctx):
        """Commands pertaining to the id survey"""

    @idsurvey.command()
    async def dosurvey(self, ctx, do_survey: bool):
        """Toggle the survey avalibility"""
        await self.config.do_survey.set(do_survey)
        await ctx.tick()

    @idsurvey.command()
    async def sometimesperc(self, ctx, percent: int):
        """Change what 'sometimes' means"""
        await self.config.sometimes_perc.set(percent)
        await ctx.tick()

    @idsurvey.command()
    async def checkbadness(self, ctx):
        """Check how good id is according to end users"""
        good = await self.config.good()
        bad = await self.config.bad()
        await ctx.send(f"{bad}/{good + bad} ({int(round(bad / (good + bad) * 100)) if good or bad else 'NaN'}%)")

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def id2(self, ctx, *, query: str):
        """Monster info (main tab)"""
        await self._do_id2(ctx, query)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def id2na(self, ctx, *, query: str):
        """Monster info (limited to NA monsters ONLY)"""
        await self._do_id2(ctx, query, server_filter=ServerFilter.na)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def id2jp(self, ctx, *, query: str):
        """Monster info (limited to JP monsters ONLY)"""
        await self._do_id2(ctx, query, server_filter=ServerFilter.jp)

    async def _do_id2(self, ctx, query: str, server_filter=ServerFilter.any):
        m, err, debug_info = await self.findMonster2(query, server_filter=server_filter)
        if m is not None:
            await self._do_idmenu(ctx, m, self.id_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def id3(self, ctx, *, query: str):
        """Monster info (main tab)"""
        await self._do_id3(ctx, query)

    async def _do_id3(self, ctx, query):
        m = await self.findMonster3(query)

        if await self.config.do_survey():
            asyncio.create_task(self.send_survey_after(ctx, query, m))

        if m is not None:
            await self._do_idmenu(ctx, m, self.id_emoji)
        else:
            await self.makeFailureMsg(ctx, query, "No monster matched")

    @commands.command(name="evos")
    @checks.bot_has_permissions(embed_links=True)
    async def evos(self, ctx, *, query: str):
        """Monster info (evolutions tab)"""
        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.evo_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command(name="mats", aliases=['evomats', 'evomat'])
    @checks.bot_has_permissions(embed_links=True)
    async def evomats(self, ctx, *, query: str):
        """Monster info (evo materials tab)"""
        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.mats_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def pantheon(self, ctx, *, query: str):
        """Monster info (pantheon tab)"""
        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        if m is not None:
            menu = await self._do_idmenu(ctx, m, self.pantheon_emoji)
            if menu == EMBED_NOT_GENERATED:
                await ctx.send(inline('Not a pantheon monster'))
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def skillups(self, ctx, *, query: str):
        """Monster info (evolutions tab)"""
        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        if m is not None:
            menu = await self._do_idmenu(ctx, m, self.skillups_emoji)
            if menu == EMBED_NOT_GENERATED:
                await ctx.send(inline('No skillups available'))
        else:
            await self.makeFailureMsg(ctx, query, err)

    async def _do_idmenu(self, ctx, m, starting_menu_emoji):
        DGCOG = self.bot.get_cog("Dadguide")
        db_context = DGCOG.database

        alt_versions = db_context.graph.get_alt_monsters_by_id(m.monster_id)
        emoji_to_embed = await self.get_id_emoji_options(ctx,
                                                         m=m, scroll=sorted({*alt_versions}, key=lambda
                x: x.monster_id) if self.settings.checkEvoID(
                ctx.author.id) else [], menu_type=1)

        return await self._do_menu(
            ctx,
            starting_menu_emoji,
            IdEmojiUpdater(ctx, emoji_to_embed, pad_info=self,
                           m=m, selected_emoji=starting_menu_emoji, bot=self.bot,
                           db_context=db_context)
        )

    async def _do_scrollmenu(self, ctx, m, ms, starting_menu_emoji):
        emoji_to_embed = await self.get_id_emoji_options(ctx, m=m, scroll=ms)
        return await self._do_menu(
            ctx,
            starting_menu_emoji,
            ScrollEmojiUpdater(ctx, emoji_to_embed, pad_info=self, bot=self.bot,
                               m=m, ms=ms, selected_emoji=starting_menu_emoji)
        )

    async def get_id_emoji_options(self, ctx, m=None, scroll=None, menu_type=0):
        if scroll is None:
            scroll = []
        DGCOG = self.bot.get_cog("Dadguide")
        db_context = DGCOG.database

        menu = IdMenu(ctx, db_context=db_context, allowed_emojis=self.get_emojis())

        id_embed = await menu.make_embed(m)
        evo_embed = await menu.make_evo_embed_v2(m)
        mats_embed = await menu.make_evo_mats_embed(m)
        animated = m.has_animation
        pic_embed = await menu.make_picture_embed(m, animated=animated)
        other_info_embed = await menu.make_otherinfo_embed(m)

        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.id_emoji] = id_embed
        emoji_to_embed[self.evo_emoji] = evo_embed
        emoji_to_embed[self.mats_emoji] = mats_embed
        emoji_to_embed[self.pic_emoji] = pic_embed
        pantheon_embed = await menu.make_pantheon_embed(m)
        if pantheon_embed:
            emoji_to_embed[self.pantheon_emoji] = pantheon_embed

        skillups_embed = await menu.make_skillups_embed(m)
        if skillups_embed:
            emoji_to_embed[self.skillups_emoji] = skillups_embed

        emoji_to_embed[self.other_info_emoji] = other_info_embed

        # it's impossible for the previous/next ones to be accessed because
        # IdEmojiUpdater won't allow it, however they have to be defined
        # so that the buttons display in the first place

        if len(scroll) > 1 and menu_type != 1:
            emoji_to_embed[self.first_monster_emoji] = None
        if len(scroll) != 1:
            emoji_to_embed[self.previous_monster_emoji] = None
            emoji_to_embed[self.next_monster_emoji] = None
        if len(scroll) > 1 and menu_type != 1:
            emoji_to_embed[self.last_monster_emoji] = None

        # remove emoji needs to be last
        emoji_to_embed[self.remove_emoji] = self.menu.reaction_delete_message
        return emoji_to_embed

    async def _do_evolistmenu(self, ctx, sm):
        DGCOG = self.bot.get_cog("Dadguide")
        db_context = DGCOG.database

        monsters = db_context.graph.get_alt_monsters_by_id(sm.monster_id)
        monsters.sort(key=lambda x: x.monster_id)

        emoji_to_embed = OrderedDict()
        menu = IdMenu(ctx, db_context=db_context, allowed_emojis=self.get_emojis())
        starting_menu_emoji = None
        for idx, m in enumerate(monsters):
            chars = "0123456789\N{KEYCAP TEN}ABCDEFGHI"
            if idx > 19:
                await ctx.send(
                    "There are too many evos for this monster to display.  Try using `{}evolist`.".format(ctx.prefix))
                return
            else:
                emoji = char_to_emoji(chars[idx])
            emoji_to_embed[emoji] = await menu.make_embed(m)
            if m.monster_id == sm.monster_id:
                starting_menu_emoji = emoji

        return await self._do_menu(ctx, starting_menu_emoji, EmojiUpdater(emoji_to_embed), timeout=60)

    async def _do_menu(self, ctx, starting_menu_emoji, emoji_to_embed, timeout=30):
        if starting_menu_emoji not in emoji_to_embed.emoji_dict:
            # Selected menu wasn't generated for this monster
            return EMBED_NOT_GENERATED

        emoji_to_embed.emoji_dict[self.remove_emoji] = self.menu.reaction_delete_message

        try:
            result_msg, result_embed = await self.menu.custom_menu(ctx, emoji_to_embed,
                                                                   starting_menu_emoji, timeout=timeout)
            if result_msg and result_embed:
                # Message is finished but not deleted, clear the footer
                result_embed.set_footer(text=discord.Embed.Empty)
                await result_msg.edit(embed=result_embed)
        except Exception as ex:
            logger.error('Menu failure', exc_info=True)

    @commands.command(aliases=['img'])
    @checks.bot_has_permissions(embed_links=True)
    async def pic(self, ctx, *, query: str):
        """Monster info (full image tab)"""
        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.pic_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def links(self, ctx, *, query: str):
        """Monster links"""
        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        if m is not None:
            menu = IdMenu(ctx)
            embed = await menu.make_links_embed(m)
            await ctx.send(embed=embed)

        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command(aliases=['stats'])
    @checks.bot_has_permissions(embed_links=True)
    async def otherinfo(self, ctx, *, query: str):
        """Monster info (misc info tab)"""
        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.other_info_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def buttoninfo(self, ctx, *, query: str):
        """Button farming theorycrafting info"""
        monster, err, _ = await self.findMonsterCustom(ctx, query)
        if monster is None:
            await self.makeFailureMsg(ctx, query, err)
            return
        DGCOG = self.bot.get_cog("Dadguide")
        info = button_info.get_info(DGCOG, monster)
        info_str = button_info.to_string(monster, info)
        for page in pagify(info_str):
            await ctx.send(box(page))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def lookup(self, ctx, *, query: str):
        """Short info results for a monster query"""
        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        if m is not None:
            menu = IdMenu(ctx, allowed_emojis=self.get_emojis())
            embed = await menu.make_header_embed(m)
            await ctx.send(embed=embed)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def evolist(self, ctx, *, query):
        """Monster info (for all monsters in the evo tree)"""
        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        if m is not None:
            await self._do_evolistmenu(ctx, m)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command(aliases=['collabscroll'])
    @checks.bot_has_permissions(embed_links=True)
    async def seriesscroll(self, ctx, *, query: str):
        """Scroll through the monsters in a collab"""
        DGCOG = self.bot.get_cog("Dadguide")
        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        ms = DGCOG.database.get_monsters_by_series(m.series.series_id)

        ms.sort(key=lambda x: x.monster_id)
        ms = [m for m in ms if m.sell_mp >= 100]

        if not ms:
            await ctx.send("There are no monsters in that series worth more than 99 monster points.")
            return

        if m not in ms:
            m = m if m in ms else ms[0]

        if m is not None:
            await self._do_scrollmenu(ctx, m, ms, self.id_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def evoscroll(self, ctx, *, query: str):
        """Scroll through the monsters in a collab"""
        DGCOG = self.bot.get_cog("Dadguide")
        db_context: "DbContext" = DGCOG.database
        m, err, debug_info = await self.findMonsterCustom(ctx, query)

        if m is not None:
            await self._do_scrollmenu(ctx, m, sorted(db_context.graph.get_alt_monsters(m), key=lambda x: x.monster_id),
                                      self.id_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command(aliases=['leaders', 'leaderskills', 'ls'], usage="<card_1> [card_2]")
    @checks.bot_has_permissions(embed_links=True)
    async def leaderskill(self, ctx, *, whole_query):
        """Display the multiplier and leaderskills for two monsters

        Gets two monsters separated by a slash, wrapping quotes, a comma,
        or spaces (if there's only two words).
        [p]ls r sonia/ revo lu bu
        [p]ls r sonia "revo lu bu"
        [p]ls sonia lubu
        """
        DGCOG = self.bot.get_cog("Dadguide")
        db_context = DGCOG.database

        # Remove unicode quotation marks
        whole_query = re.sub("[\u201c\u201d]", '"', whole_query)

        # deliberate order in case of multiple different separators.
        for sep in ('"', '/', ',', ' '):
            if sep in whole_query:

                left_query, *right_query = [x.strip() for x in whole_query.split(sep) if x.strip()] or (
                    '', '')  # or in case of ^ls [sep] which is empty list
                # split on first separator, with if x.strip() block to prevent null values from showing up, mainly for quotes support
                # right query is the rest of query but in list form because of how .strip() works. bring it back to string form with ' '.join
                right_query = ' '.join(q for q in right_query)
                if sep == ' ':
                    # Handle a very specific failure case, user typing something like "uuvo ragdra"
                    nm, err, debug_info = await self._findMonster(whole_query)
                    if not err and left_query in nm.prefixes:
                        left_query = whole_query
                        right_query = None

                break

        else:  # no separators
            left_query, right_query = whole_query, None

        left_m, left_err, _ = await self.findMonsterCustom(ctx, left_query)
        if right_query:
            right_m, right_err, _ = await self.findMonsterCustom(ctx, right_query)
        else:
            right_m, right_err, = left_m, left_err

        err_msg = '{} query failed to match a monster: [ {} ]. If your query is multiple words, try separating the queries with / or wrap with quotes.'
        if left_err:
            await ctx.send(inline(err_msg.format('Left', left_query)))
            return
        if right_err:
            await ctx.send(inline(err_msg.format('Right', right_query)))
            return

        menu = IdMenu(ctx, db_context=db_context, allowed_emojis=self.get_emojis())
        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.ls_emoji] = await menu.make_ls_embed(left_m, right_m)
        emoji_to_embed[self.left_emoji] = await menu.make_embed(left_m)
        emoji_to_embed[self.right_emoji] = await menu.make_embed(right_m)

        await self._do_menu(ctx, self.ls_emoji, EmojiUpdater(emoji_to_embed))

    @commands.command(aliases=['lssingle'])
    @checks.bot_has_permissions(embed_links=True)
    async def leaderskillsingle(self, ctx, *, query):
        DGCOG = self.bot.get_cog("Dadguide")
        db_context = DGCOG.database

        m, err, _ = await self.findMonsterCustom(ctx, query)
        if err:
            await ctx.send(err)
            return
        menu = IdMenu(ctx, db_context=db_context, allowed_emojis=self.get_emojis())
        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.ls_emoji] = await menu.make_lssingle_embed(m)
        emoji_to_embed[self.left_emoji] = await menu.make_embed(m)

        await self._do_menu(ctx, self.ls_emoji, EmojiUpdater(emoji_to_embed))

    @commands.group()
    # @checks.is_owner()
    async def idtest(self, ctx):
        """ID Test suite subcommands"""

    @idtest.command(name="add")
    async def idt_add(self, ctx, id: int, *, query):
        async with self.config.test_suite() as suite:
            suite[query] = {'result': id, 'ts': datetime.now().timestamp()}
        await ctx.tick()

    @idtest.command(name="import")
    async def idt_import(self, ctx, *, queries):
        cases = re.findall(r'\s*(?:\d+. )?(.+?) + - (\d+) *(.*)', queries)
        async with self.config.test_suite() as suite:
            for query, result, reason in cases:
                suite[query] = {'result': int(result), 'reason': reason, 'ts': datetime.now().timestamp()}
        await ctx.tick()

    @idtest.command(name="remove", aliases=["delete", "rm"])
    async def idt_remove(self, ctx, *, item):
        async with self.config.test_suite() as suite:
            if item in suite:
                del suite[item]
            elif item.isdigit() and int(item) < len(suite):
                del suite[sorted(suite)[int(item)]]
            else:
                await ctx.react_quietly("\N{CROSS MARK}")
                return
        await ctx.tick()

    @idtest.command(name="setreason", aliases=["addreason"])
    async def idt_setreason(self, ctx, number: int, *, reason):
        async with self.config.test_suite() as suite:
            if number >= len(suite):
                await ctx.react_quietly("\N{CROSS MARK}")
                return
            suite[sorted(suite)[number]]['reason'] = reason
        await ctx.tick()

    @idtest.command(name="list")
    async def idt_list(self, ctx):
        suite = await self.config.test_suite()
        o = ""
        ml = len(max(suite, key=len))
        for c, kv in enumerate(sorted(suite.items())):
            o += f"{str(c).rjust(3)}. {kv[0].ljust(ml)} - {str(kv[1]['result']).ljust(4)}\t{kv[1].get('reason') or ''}\n"
        if not o:
            await ctx.send("There are no test cases.")
        for page in pagify(o):
            await ctx.send(box(page))

    @idtest.command(name="listrecent")
    async def idt_listrecent(self, ctx, count: int = 0):
        suite = await self.config.test_suite()
        if count == 0:
            count = len(suite)
        o = ""
        ml = len(max(suite, key=len))
        for c, kv in enumerate(sorted(suite.items(), key=lambda kv: kv[1].get('ts', 0), reverse=True)[:count]):
            o += f"{kv[0].ljust(ml)} - {str(kv[1]['result']).ljust(4)}\t{kv[1].get('reason') or ''}\n"
        if not o:
            await ctx.send("There are no test cases.")
        for page in pagify(o):
            await ctx.send(box(page))

    @idtest.command(name="run", aliases=["test"])
    async def idt_run(self, ctx):
        suite = await self.config.test_suite()
        c = 0
        o = ""
        ml = len(max(suite, key=len)) + 2
        async with ctx.typing():
            for q, r in suite.items():
                m = await self.findMonster3(q)
                if m is not None and m.monster_id != r['result'] or m is None and r['result'] >= 0:
                    reason = '   Reason: ' + r.get('reason') if 'reason' in r else ''
                    q = '"' + q + '"'
                    o += f"{q.ljust(ml)} - Ex: {r['result']}, Ac: {m and m.monster_id}{reason}\n"
                else:
                    c += 1
        if c:
            o += f"\n\nTests complete.  {c}/{len(suite)} succeeded."
        else:
            o += "\n\nAll tests succeeded."
        for page in pagify(o):
            await ctx.send(box(page))

    @commands.command()
    async def padsay(self, ctx, server, *, query: str = None):
        """Speak the voice line of a monster into your current chat"""
        voice = ctx.author.voice
        if not voice:
            await ctx.send(inline('You must be in a voice channel to use this command'))
            return
        channel = voice.channel

        speech_cog = self.bot.get_cog('Speech')
        if not speech_cog:
            await ctx.send(inline('Speech seems to be offline'))
            return

        if server.lower() not in ['na', 'jp']:
            query = server + ' ' + (query or '')
            server = 'na'
        query = query.strip().lower()

        m, err, debug_info = await self.findMonsterCustom(ctx, query)
        if m is not None:
            voice_id = m.voice_id_jp if server == 'jp' else m.voice_id_na
            if voice_id is None:
                await ctx.send(inline("No voice file found for " + m.name_en))
                return
            base_dir = self.settings.voiceDir()
            voice_file = os.path.join(base_dir, server, '{0:03d}.wav'.format(voice_id))
            header = '{} ({})'.format(MonsterHeader.short(m), server)
            if not os.path.exists(voice_file):
                await ctx.send(inline('Could not find voice for ' + header))
                return
            await ctx.send('Speaking for ' + header)
            await speech_cog.play_path(channel, voice_file)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.group(aliases=['idmode'])
    async def idset(self, ctx):
        """id settings configuration"""

    @idset.command()
    async def scroll(self, ctx, value):
        """Switch between number scroll and evo scroll

        [p]idset scroll number
        [p]idset scroll evo"""
        if value in ['evo', 'default']:
            if self.settings.setEvoID(ctx.author.id):
                await ctx.tick()
            else:
                await ctx.send(inline("You're already using evo mode"))
        elif value in ['number']:
            if self.settings.rmEvoID(ctx.author.id):
                await ctx.tick()
            else:
                await ctx.send(inline("You're already using number mode"))
        else:
            await ctx.send("id_type must be `number` or `evo`")

    @idset.command()
    async def survey(self, ctx, value):
        """Change how often you see the id survey

        [p]idset survey always     (Always see survey after using id)
        [p]idset survey sometimes  (See survey some of the time after using id)
        [p]idset survey never      (Never see survey after using id D:)"""
        vals = ['always', 'sometimes', 'never']
        if value in vals:
            await self.config.user(ctx.author).survey_mode.set(vals.index(value))
            await ctx.tick()
        else:
            await ctx.send("value must be `always`, `sometimes`, or `never`")

    @idset.command()
    async def beta(self, ctx, value: bool = True):
        """Opt in (or out D:) to the id3 beta test!"""
        await self.config.user(ctx.author).beta_id3.set(value)
        await ctx.tick()

    @idset.command()
    @checks.is_owner()
    async def betacount(self, ctx):
        """Check the number of beta testers"""
        c = 0
        for v in (await self.config.all_users()).values():
            if v['beta_id3']:
                c += 1
        await ctx.send(inline(str(c) + " user(s) have opted in."))

    @is_donor()
    @idset.command()
    async def embedcolor(self, ctx, *, color):
        """(DONOR ONLY) Change the color of all your ID embeds!

        Examples:
        [p]idset embedcolor green
        [p]idset embedcolor #a10000
        [p]idset embedcolor random

        Picking random will choose a random hex code every time you use [p]id!
        """
        if color in COLORS:
            await self.config.user(ctx.author).color.set(COLORS[color])
        elif re.match(r"^#?[0-9a-fA-F]{6}$", color):
            await self.config.user(ctx.author).color.set(int(color.lstrip("#"), 16))
        else:
            await ctx.send("Invalid color!  Valid colors are any hexcode and:\n" + ", ".join(COLORS))
            return
        await ctx.tick()

    @commands.group()
    @checks.is_owner()
    async def padinfo(self, ctx):
        """PAD info management"""

    @padinfo.group()
    @checks.is_owner()
    async def emojiservers(self, ctx):
        """Emoji server subcommand"""

    @emojiservers.command(name="add")
    @checks.is_owner()
    async def es_add(self, ctx, server_id: int):
        """Add the emoji server by ID"""
        ess = self.settings.emojiServers()
        if server_id not in ess:
            ess.append(server_id)
            self.settings.save_settings()
        await ctx.tick()

    @emojiservers.command(name="remove", aliases=['rm', 'del'])
    @checks.is_owner()
    async def es_rm(self, ctx, server_id: int):
        """Remove the emoji server by ID"""
        ess = self.settings.emojiServers()
        if server_id not in ess:
            await ctx.send("That emoji server is not set.")
            return
        ess.remove(server_id)
        self.settings.save_settings()
        await ctx.tick()

    @emojiservers.command(name="list", aliases=['show'])
    @checks.is_owner()
    async def es_show(self, ctx):
        """List the emoji servers by ID"""
        ess = self.settings.emojiServers()
        await ctx.send(box("\n".join(str(s) for s in ess)))

    @padinfo.command()
    @checks.is_owner()
    async def setvoicepath(self, ctx, *, path=''):
        """Set path to the voice direcory"""
        self.settings.setVoiceDir(path)
        await ctx.tick()

    @checks.is_owner()
    @padinfo.command()
    async def iddiff(self, ctx):
        """Runs the diff checker for id and id2"""
        await ctx.send("Running diff checker...")
        hist_aggreg = list(self.historic_lookups)
        s = 0
        f = []
        async for c, query in AsyncIter(enumerate(hist_aggreg)):
            m1, err1, debug_info1 = await self.findMonsterCustom(ctx, query)
            m2, err2, debug_info2 = await self.findMonster2(query)
            if c % 50 == 0:
                await ctx.send(inline("{}/{} complete.".format(c, len(hist_aggreg))))
            if m1 == m2 or (m1 and m2 and m1.monster_id == m2.monster_id):
                s += 1
                continue

            f.append((query,
                      [m1.monster_id if m1 else None, m2.monster_id if m2 else None],
                      [err1, err2],
                      [debug_info1, debug_info2]
                      ))
            if m1 and m2:
                await ctx.send("Major Discrepency: `{}` -> {}/{}".format(query, m1.name_en, m2.name_en))
        await ctx.send("Done running diff checker.  {}/{} passed.".format(s, len(hist_aggreg)))
        file = discord.File(BytesIO(json.dumps(f).encode()), filename="diff.json")
        await ctx.send(file=file)

    def get_emojis(self):
        server_ids = [int(sid) for sid in self.settings.emojiServers()]
        return [e for g in self.bot.guilds if g.id in server_ids for e in g.emojis]

    async def makeFailureMsg(self, ctx, query: str, err):
        if await self.config.user(ctx.author).beta_id3():
            await ctx.send("Sorry, your query {0} didn't match any results :(\n"
                           "See <{2}> for "
                           "documentation on `{1.prefix}id`! You can also  run `{1.prefix}idhelp <monster id>` to get "
                           "help with querying a specific monster.".format(inline(query), ctx, IDGUIDE))
            return
        msg = ('Lookup failed: {0}.\n'
               'Try one of <id>, <name>, [argbld]/[rgbld] <name>. '
               'Unexpected results? Use {1.prefix}helpid for more info.').format(err, ctx)
        await ctx.send(box(msg))
        await ctx.send('Looking for the beta test? Type `{0.prefix}idset beta y`'.format(ctx))

    async def findMonsterCustom(self, ctx, query, server_filter=ServerFilter.any):
        if await self.config.user(ctx.author).beta_id3():
            m = await self.findMonster3(query)
            if m:
                return m, "", ""
            else:
                return None, "Monster not found", ""
        else:
            return await self.findMonster1(query, server_filter)

    async def findMonster1(self, query, server_filter=ServerFilter.any):
        query = rmdiacritics(query)
        nm, err, debug_info = await self._findMonster(query, server_filter)

        monster_no = nm.monster_id if nm else -1
        self.historic_lookups[query] = monster_no
        json.dump(self.historic_lookups, open(self.historic_lookups_file_path, "w+"))

        m = self.get_monster(nm.monster_id) if nm else None

        return m, err, debug_info

    async def _findMonster(self, query, server_filter=ServerFilter.any) -> "NamedMonster":
        while self.index_lock.locked():
            await asyncio.sleep(1)

        if server_filter.value == ServerFilter.any.value:
            monster_index = self.index_all
        elif server_filter.value == ServerFilter.na.value:
            monster_index = self.index_na
        elif server_filter.value == ServerFilter.jp.value:
            monster_index = self.index_jp
        else:
            raise ValueError("server_filter must be type ServerFilter not " + str(type(server_filter)))
        return monster_index.find_monster(query)

    async def findMonster2(self, query, server_filter=ServerFilter.any):
        query = rmdiacritics(query)
        nm, err, debug_info = await self._findMonster2(query, server_filter)

        monster_no = nm.monster_id if nm else -1
        self.historic_lookups_id2[query] = monster_no
        json.dump(self.historic_lookups_id2, open(self.historic_lookups_file_path_id2, "w+"))

        m = self.get_monster(nm.monster_id) if nm else None

        return m, err, debug_info

    async def _findMonster2(self, query, server_filter=ServerFilter.any):
        while self.index_lock.locked():
            await asyncio.sleep(1)

        if server_filter == ServerFilter.any:
            monster_index = self.index_all
        elif server_filter == ServerFilter.na:
            monster_index = self.index_na
        elif server_filter == ServerFilter.jp:
            monster_index = self.index_jp
        else:
            raise ValueError("server_filter must be type ServerFilter not " + str(type(server_filter)))
        return monster_index.find_monster2(query)

    async def findMonster3(self, query):
        m = await self._findMonster3(query)

        monster_no = m.monster_id if m else -1
        self.historic_lookups_id3[query] = monster_no
        json.dump(self.historic_lookups_id3, open(self.historic_lookups_file_path_id3, "w+"))

        return m

    async def _findMonster3(self, query):
        DGCOG = self.bot.get_cog("Dadguide")
        await DGCOG.wait_until_ready()
        if DGCOG is None:
            raise ValueError("Dadguide cog is not loaded")

        query = rmdiacritics(query).lower()
        mod_tokens, neg_mod_tokens, name_query_tokens = find_monster.interpret_query(query, DGCOG.index2)

        print(mod_tokens, name_query_tokens)

        if name_query_tokens:
            monster_gen, monster_score = find_monster.process_name_tokens(name_query_tokens, DGCOG.index2)
            if monster_gen is None:
                # No monsters match the given name tokens
                return
        else:
            # There are no name tokens in the query
            monster_gen = {*DGCOG.database.get_all_monsters()}
            monster_score = defaultdict(int)

        # Expand search to the evo tree
        monster_gen = find_monster.get_monster_evos(DGCOG.database, monster_gen, monster_score)
        monster_gen = find_monster.process_modifiers(mod_tokens, neg_mod_tokens, monster_score, monster_gen,
                                                     DGCOG.index2.modifiers)
        if not monster_gen:
            # no modifiers match any monster in the evo tree
            return

        print({k: v for k, v in monster_score.items() if k in monster_gen})

        # Return most likely candidate based on query.
        mon = max(monster_gen,
                  key=lambda m: (monster_score[m],
                                 not m.is_equip,
                                 bool(m.monster_id > 10000 and re.search(r"\d{4}", query)), # Match na on id overlap
                                 series_priority.get(m.series.series_type),
                                 m.on_na if m.series.series_type == "collab" else 0,
                                 DGCOG.database.graph.monster_is_rem_evo(m),
                                 -DGCOG.database.graph.get_base_id(m),
                                 m.rarity,
                                 m.monster_no_na))

        return mon

    @commands.command(aliases=["iddebug"])
    async def debugid(self, ctx, *, query):
        """Get helpful id information about a monster"""
        DGCOG = self.bot.get_cog("Dadguide")
        m = await self.findMonster3(query)
        if m is None:
            await ctx.send(box("Your query didn't match any monsters."))
            return
        bm = DGCOG.database.graph.get_base_monster(m)
        pfxs = DGCOG.index2.modifiers[m]
        EVOANDTYPE = DGCOG.token_maps.EVO_TOKENS.union(DGCOG.token_maps.TYPE_TOKENS)
        o = (f"[{m.monster_id}] {m.name_en}\n"
             f"Base: [{bm.monster_id}] {bm.name_en}\n"
             f"Series: {m.series.name_en} ({m.series_id})\n\n"
             f"[Name Tokens] {' '.join(sorted(t for t, ms in DGCOG.index2.tokens.items() if m in ms))}\n\n"
             f"[Manual Tokens]\n"
             f"     Treenames: {' '.join(sorted(t for t, ms in DGCOG.index2.manual_tree.items() if m in ms))}\n"
             f"     Nicknames: {' '.join(sorted(t for t, ms in DGCOG.index2.manual_nick.items() if m in ms))}\n\n"
             f"[Modifier Tokens]\n"
             f"     Attribute: {' '.join(sorted(t for t in pfxs if t in DGCOG.token_maps.COLOR_TOKENS))}\n"
             f"     Awakening: {' '.join(sorted(t for t in pfxs if t in DGCOG.token_maps.AWAKENING_TOKENS))}\n"
             f"    Evo & Type: {' '.join(sorted(t for t in pfxs if t in EVOANDTYPE))}\n"
             f"         Other: {' '.join(sorted(t for t in pfxs if t not in DGCOG.token_maps.OTHER_HIDDEN_TOKENS))}\n")
        for page in pagify(o):
            await ctx.send(box(page))

    @commands.command(aliases=['helpid'])
    async def idhelp(self, ctx, *, query=""):
        """Get help with an id query"""
        await ctx.send("See <{0}> for documentation on {1.prefix}id!".format(IDGUIDE, ctx))
        if query:
            await self.debugid(ctx, query=query)


    @commands.command()
    async def exportmodifiers(self, ctx):
        DGCOG = self.bot.get_cog("Dadguide")
        tms = DGCOG.token_maps
        o = ("Jump to:\n\n"
             "* [Types](#types)\n"
             "* [Evolutions](#evolutions)\n"
             "* [Misc](#misc)\n"
             "* [Awakenings](#awakenings)\n"
             "* [Attributes](#attributes)\n\n\n\n")

        anames = DGCOG.database.get_all_awoken_skills()

        etable = [(k.value, ", ".join(map(inline, v))) for k, v in tms.EVO_MAP.items()]
        o += "\n\n### Evolutions\n\n" + tabulate(etable, headers=["Meaning", "Tokens"], tablefmt="github")
        ttable = [(k.name, ", ".join(map(inline, v))) for k, v in tms.TYPE_MAP.items()]
        o += "\n\n### Types\n\n" + tabulate(ttable, headers=["Meaning", "Tokens"], tablefmt="github")
        mtable = [(k.value, ", ".join(map(inline, v))) for k, v in tms.MISC_MAP.items()]
        o += "\n\n### Misc\n\n" + tabulate(mtable, headers=["Meaning", "Tokens"], tablefmt="github")
        atable = [(anames[k.value - 1].name_en, ", ".join(map(inline, v))) for k, v in tms.AWOKEN_MAP.items()]
        o += "\n\n### Awakenings\n\n" + tabulate(atable, headers=["Meaning", "Tokens"], tablefmt="github")
        ctable = [(k.name.replace("Nil", "None"), ", ".join(map(inline, v))) for k, v in tms.COLOR_MAP.items()]
        ctable += [("Sub " + k.name.replace("Nil", "None"), ", ".join(map(inline, v))) for k, v in
                   tms.SUB_COLOR_MAP.items()]
        for k, v in tms.DUAL_COLOR_MAP.items():
            k0name = k[0].name.replace("Nil", "None")
            k1name = k[1].name.replace("Nil", "None")
            ctable.append((k0name + "/" + k1name, ", ".join(map(inline, v))))
        o += "### Attributes\n\n" + tabulate(ctable, headers=["Meaning", "Tokens"], tablefmt="github")

        await ctx.send(file=text_to_file(o, filename="table.md"))


class PadInfoSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'animation_dir': '',
            'alt_id_optout': [],
            'voice_dir_path': '',
            'emoji_use': {},
        }
        return config

    def emojiServers(self):
        key = 'emoji_servers'
        if key not in self.bot_settings:
            self.bot_settings[key] = []
        return self.bot_settings[key]

    def setEmojiServers(self, emoji_servers):
        es = self.emojiServers()
        es.clear()
        es.extend(emoji_servers)
        self.save_settings()

    def setEvoID(self, user_id):
        if self.checkEvoID(user_id):
            return False
        self.bot_settings['alt_id_optout'].remove(user_id)
        self.save_settings()
        return True

    def rmEvoID(self, user_id):
        if not self.checkEvoID(user_id):
            return False
        self.bot_settings['alt_id_optout'].append(user_id)
        self.save_settings()
        return True

    def checkEvoID(self, user_id):
        return user_id not in self.bot_settings['alt_id_optout']

    def setVoiceDir(self, path):
        self.bot_settings['voice_dir_path'] = path
        self.save_settings()

    def voiceDir(self):
        return self.bot_settings['voice_dir_path']

    def log_emoji(self, emote):
        self.bot_settings['emoji_use'][emote] = self.bot_settings['emoji_use'].get(emote, 0) + 1
        self.save_settings()
