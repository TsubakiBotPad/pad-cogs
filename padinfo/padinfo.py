import asyncio
import discord
import json
import logging
import os
import prettytable
import random
import traceback
import tsutils
import urllib.parse
from io import BytesIO
from collections import OrderedDict
from enum import Enum
from redbot.core import checks, commands, data_manager, Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, inline
from tsutils import CogSettings, EmojiUpdater, Menu, char_to_emoji, rmdiacritics, safe_read_json, confirm_message

from .find_monster import prefix_to_filter

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dadguide.database_context import DbContext
    from dadguide.models.monster_model import MonsterModel

logger = logging.getLogger('red.padbot-cogs.padinfo')

HELP_MSG = """
{0.prefix}helpid : shows this message
{0.prefix}id <query> : look up a monster and show a link to puzzledragonx
{0.prefix}pic <query> : Look up a monster and display its image inline

Options for <query>
    <id> : Find a monster by ID
        {0.prefix}id 1234 (picks sun quan)
    <name> : Take the best guess for a monster, picks the most recent monster
        {0.prefix}id kali (picks mega awoken d kali)
    <prefix> <name> : Limit by element or awoken, e.g.
        {0.prefix}id ares  (selects the most recent, revo ares)
        {0.prefix}id aares (explicitly selects awoken ares)
        {0.prefix}id a ares (spaces work too)
        {0.prefix}id rd ares (select a specific evo for ares, the red/dark one)
        {0.prefix}id r/d ares (slashes, spaces work too)

computed nickname list and overrides: https://docs.google.com/spreadsheets/d/1EoZJ3w5xsXZ67kmarLE4vfrZSIIIAfj04HXeZVST3eY/edit
submit an override suggestion: https://docs.google.com/forms/d/1kJH9Q0S8iqqULwrRqB9dSxMOMebZj6uZjECqi4t9_z0/edit"""

EMBED_NOT_GENERATED = -1

INFO_PDX_TEMPLATE = 'http://www.puzzledragonx.com/en/monster.asp?n={}'

MEDIA_PATH = 'https://d1kpnpud0qoyxf.cloudfront.net/media/'
RPAD_PIC_TEMPLATE = MEDIA_PATH + 'portraits/{0:05d}.png?cachebuster=2'
RPAD_PORTRAIT_TEMPLATE = MEDIA_PATH + 'icons/{0:05d}.png'
VIDEO_TEMPLATE = MEDIA_PATH + 'animated_portraits/{0:05d}.mp4'
GIF_TEMPLATE = MEDIA_PATH + 'animated_portraits/{0:05d}.gif'
ORB_SKIN_TEMPLATE = MEDIA_PATH + 'orb_skins/jp/{0:03d}.png'
ORB_SKIN_CB_TEMPLATE = MEDIA_PATH + 'orb_skins/jp/{0:03d}cb.png'

YT_SEARCH_TEMPLATE = 'https://www.youtube.com/results?search_query={}'
SKYOZORA_TEMPLATE = 'http://pad.skyozora.com/pets/{}'
ILMINA_TEMPLATE = 'https://ilmina.com/#/CARD/{}'


class ServerFilter(Enum):
    any = 0
    na = 1
    jp = 2


def get_pdx_url(m):
    return INFO_PDX_TEMPLATE.format(tsutils.get_pdx_id(m))


def get_portrait_url(m):
    return RPAD_PORTRAIT_TEMPLATE.format(m.monster_id)


def get_pic_url(m):
    return RPAD_PIC_TEMPLATE.format(m.monster_id)


def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='padinfo')), file_name)


class IdEmojiUpdater(EmojiUpdater):
    def __init__(self, emoji_to_embed, m: "MonsterModel" = None,
                 pad_info=None, selected_emoji=None, bot=None,
                 db_context: "DbContext" = None):
        self.emoji_dict = emoji_to_embed
        self.m = m
        self.pad_info = pad_info
        self.selected_emoji = selected_emoji
        self.bot = bot
        self.db_context = db_context

        self.pad_info.settings.log_emoji("start_" + selected_emoji)

    def on_update(self, ctx, selected_emoji):
        evoID = self.pad_info.settings.checkEvoID(ctx.author.id)
        self.pad_info.settings.log_emoji(selected_emoji)
        if evoID:
            evos = sorted({*self.db_context.graph.get_alt_cards(self.m.monster_id)})
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

        self.emoji_dict = self.pad_info.get_id_emoji_options(
            m=self.m, scroll=sorted(
                {*self.db_context.graph.get_alt_cards(self.m.monster_id)}) if evoID else [], menu_type=1)
        return True


class ScrollEmojiUpdater(EmojiUpdater):
    def __init__(self, emoji_to_embed, m: "MonsterModel" = None,
                 ms: "List[int]" = None, selected_emoji=None, pad_info=None, bot=None):
        self.emoji_dict = emoji_to_embed
        self.m = m
        self.ms = ms
        self.pad_info = pad_info
        self.selected_emoji = selected_emoji
        self.bot = bot

    def on_update(self, ctx, selected_emoji):
        DGCOG = self.bot.get_cog('Dadguide')
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

        self.emoji_dict = self.pad_info.get_id_emoji_options(m=self.m, scroll=self.ms)
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

        self.config = Config.get_conf(self, identifier=9401770)
        self.config.register_user(survey_mode=0)
        self.config.register_global(sometimes_perc=20, good=0, bad=0, do_survey=False)

    def cog_unload(self):
        # Manually nulling out database because the GC for cogs seems to be pretty shitty
        self.index_all = None
        self.index_na = None
        self.index_jp = None
        self.historic_lookups = {}
        self.historic_lookups_id2 = {}

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
        m, err, debug_info = await self.findMonster(query)
        if m is not None:
            await ctx.send(monsterToHeader(m))
            await ctx.send(box(m.name_ja))
        else:
            await ctx.send(self.makeFailureMsg(err))

    @commands.command(name="id", aliases="iD Id ID".split())
    @checks.bot_has_permissions(embed_links=True)
    async def _id(self, ctx, *, query: str):
        """Monster info (main tab)"""
        prefix = ctx.prefix + "id"
        query = prefix.join(filter(None, query.split(prefix)))
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
        m, err, debug_info = await self.findMonster(query, server_filter=server_filter)

        if await self.config.do_survey():
            asyncio.create_task(self.send_survey_after(ctx, query, m.name_en if m else "None"))
        if m is not None:
            await self._do_idmenu(ctx, m, self.id_emoji)
        else:
            await ctx.send(self.makeFailureMsg(err))

    async def send_survey_after(self, ctx, query, result):
        sm = await self.config.user(ctx.author).survey_mode()
        sms = [1, await self.config.sometimes_perc() / 100, 0][sm]
        if random.random() < sms:
            params = urllib.parse.urlencode({'usp': 'pp_url', 'entry.154088017': query, 'entry.173096863': result})
            url = "https://docs.google.com/forms/d/e/1FAIpQLSf66fE76epgslagdYteQR68HZAhxM43bmgsvurEzmHKsbaBDA/viewform?" + params
            await asyncio.sleep(1)
            userres = await tsutils.confirm_message(ctx, "Was this the monster you were looking for?",
                                                    yemoji=char_to_emoji('y'), nemoji=char_to_emoji('n'))
            if userres is True:
                await self.config.good.set(await self.config.good() + 1)
            elif userres is False:
                await self.config.bad.set(await self.config.bad() + 1)
                m = await ctx.send(f"Oh no!  You can help the Tsubaki team give better results"
                                   f" by filling out this survey!\nPRO TIP: Use `{ctx.prefix}idmode"
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
            await ctx.send(self.makeFailureMsg(err))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def id3(self, ctx, *, query: str):
        """Monster info (main tab)"""
        await self._do_id3(ctx, query)

    async def _do_id3(self, ctx, query: str):
        m = await self.findMonster3(query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.id_emoji)
        else:
            await ctx.send("whoops")

    @commands.command(name="evos")
    @checks.bot_has_permissions(embed_links=True)
    async def evos(self, ctx, *, query: str):
        """Monster info (evolutions tab)"""
        m, err, debug_info = await self.findMonster(query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.evo_emoji)
        else:
            await ctx.send(self.makeFailureMsg(err))

    @commands.command(name="mats", aliases=['evomats', 'evomat'])
    @checks.bot_has_permissions(embed_links=True)
    async def evomats(self, ctx, *, query: str):
        """Monster info (evo materials tab)"""
        m, err, debug_info = await self.findMonster(query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.mats_emoji)
        else:
            await ctx.send(self.makeFailureMsg(err))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def pantheon(self, ctx, *, query: str):
        """Monster info (pantheon tab)"""
        m, err, debug_info = await self.findMonster(query)
        if m is not None:
            menu = await self._do_idmenu(ctx, m, self.pantheon_emoji)
            if menu == EMBED_NOT_GENERATED:
                await ctx.send(inline('Not a pantheon monster'))
        else:
            await ctx.send(self.makeFailureMsg(err))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def skillups(self, ctx, *, query: str):
        """Monster info (evolutions tab)"""
        m, err, debug_info = await self.findMonster(query)
        if m is not None:
            menu = await self._do_idmenu(ctx, m, self.skillups_emoji)
            if menu == EMBED_NOT_GENERATED:
                await ctx.send(inline('No skillups available'))
        else:
            await ctx.send(self.makeFailureMsg(err))

    async def _do_idmenu(self, ctx, m, starting_menu_emoji):
        DGCOG = self.bot.get_cog("Dadguide")
        db_context = DGCOG.database

        alt_versions = db_context.graph.get_alt_monsters_by_id(m.monster_id)
        emoji_to_embed = self.get_id_emoji_options(
            m=m, scroll=sorted({*alt_versions}, key=lambda x: x.monster_id) if self.settings.checkEvoID(ctx.author.id) else [], menu_type=1)

        return await self._do_menu(
            ctx,
            starting_menu_emoji,
            IdEmojiUpdater(emoji_to_embed, pad_info=self,
                           m=m, selected_emoji=starting_menu_emoji, bot=self.bot,
                           db_context=db_context)
        )

    async def _do_scrollmenu(self, ctx, m, ms, starting_menu_emoji):
        emoji_to_embed = self.get_id_emoji_options(m=m, scroll=ms)
        return await self._do_menu(
            ctx,
            starting_menu_emoji,
            ScrollEmojiUpdater(emoji_to_embed, pad_info=self, bot=self.bot,
                               m=m, ms=ms, selected_emoji=starting_menu_emoji)
        )

    def get_id_emoji_options(self, m=None, scroll=[], menu_type=0):
        DGCOG = self.bot.get_cog("Dadguide")
        db_context = DGCOG.database

        id_embed = monsterToEmbed(m, self.get_emojis(), db_context)
        evo_embed = monsterToEvoEmbed(m, self.get_emojis(), db_context)
        mats_embed = monsterToEvoMatsEmbed(m, db_context, self.get_emojis())
        animated = m.has_animation
        pic_embed = monsterToPicEmbed(m, self.get_emojis(), animated=animated)
        other_info_embed = monsterToOtherInfoEmbed(m, db_context, self.get_emojis())

        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.id_emoji] = id_embed
        emoji_to_embed[self.evo_emoji] = evo_embed
        emoji_to_embed[self.mats_emoji] = mats_embed
        emoji_to_embed[self.pic_emoji] = pic_embed
        pantheon_embed = monsterToPantheonEmbed(m, db_context, self.get_emojis())
        if pantheon_embed:
            emoji_to_embed[self.pantheon_emoji] = pantheon_embed

        skillups_embed = monsterToSkillupsEmbed(m, db_context, self.get_emojis())
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
        for idx, m in enumerate(monsters):
            chars = "0123456789\N{KEYCAP TEN}ABCDEFGHI"
            if idx > 19:
                await ctx.send("There are too many evos for this monster to display.  Try using `{}evolist`.".format(ctx.prefix))
                return
            else:
                emoji = char_to_emoji(chars[idx])
            emoji_to_embed[emoji] = monsterToEmbed(m, self.get_emojis(), db_context)
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
            logger.error('Menu failure', exc_info=1)

    @commands.command(aliases=['img'])
    @checks.bot_has_permissions(embed_links=True)
    async def pic(self, ctx, *, query: str):
        """Monster info (full image tab)"""
        m, err, debug_info = await self.findMonster(query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.pic_emoji)
        else:
            await ctx.send(self.makeFailureMsg(err))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def links(self, ctx, *, query: str):
        """Monster links"""
        m, err, debug_info = await self.findMonster(query)
        if m is not None:
            embed = monsterToBaseEmbed(m)
            embed.description = "\n[YouTube]({}) | [Skyozora]({}) | [PDX]({}) | [Ilimina]({})".format(
                YT_SEARCH_TEMPLATE.format(urllib.parse.quote(m.name_ja)),
                SKYOZORA_TEMPLATE.format(m.monster_no_jp),
                INFO_PDX_TEMPLATE.format(m.monster_no_jp),
                ILMINA_TEMPLATE.format(m.monster_no_jp))
            embed.set_footer(text='')
            await ctx.send(embed=embed)

        else:
            await ctx.send(self.makeFailureMsg(err))

    @commands.command(aliases=['stats'])
    @checks.bot_has_permissions(embed_links=True)
    async def otherinfo(self, ctx, *, query: str):
        """Monster info (misc info tab)"""
        m, err, debug_info = await self.findMonster(query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.other_info_emoji)
        else:
            await ctx.send(self.makeFailureMsg(err))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def lookup(self, ctx, *, query: str):
        """Short info results for a monster query"""
        m, err, debug_info = await self.findMonster(query)
        if m is not None:
            embed = monsterToHeaderEmbed(m, self.get_emojis())
            await ctx.send(embed=embed)
        else:
            await ctx.send(self.makeFailureMsg(err))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def evolist(self, ctx, *, query):
        """Monster info (for all monsters in the evo tree)"""
        m, err, debug_info = await self.findMonster(query)
        if m is not None:
            await self._do_evolistmenu(ctx, m)
        else:
            await ctx.send(self.makeFailureMsg(err))

    @commands.command(aliases=['collabscroll'])
    @checks.bot_has_permissions(embed_links=True)
    async def seriesscroll(self, ctx, *, query: str):
        """Scroll through the monsters in a collab"""
        DGCOG = self.bot.get_cog("Dadguide")
        m, err, debug_info = await self.findMonster(query)
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
            await ctx.send(self.makeFailureMsg(err))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def evoscroll(self, ctx, *, query: str):
        """Scroll through the monsters in a collab"""
        DGCOG = self.bot.get_cog("Dadguide")
        db_context: "DbContext" = DGCOG.database
        m, err, debug_info = await self.findMonster(query)

        if m is not None:
            await self._do_scrollmenu(ctx, m, sorted(db_context.graph.get_alt_monsters(m), key=lambda x: x.monster_id), self.id_emoji)
        else:
            await ctx.send(self.makeFailureMsg(err))

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

        left_m, left_err, _ = await self.findMonster(left_query)
        if right_query:
            right_m, right_err, _ = await self.findMonster(right_query)
        else:
            right_m, right_err, = left_m, left_err

        err_msg = '{} query failed to match a monster: [ {} ]. If your query is multiple words, try separating the queries with / or wrap with quotes.'
        if left_err:
            await ctx.send(inline(err_msg.format('Left', left_query)))
            return
        if right_err:
            await ctx.send(inline(err_msg.format('Right', right_query)))
            return

        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.ls_emoji] = monstersToLsEmbed(left_m, right_m)
        emoji_to_embed[self.left_emoji] = monsterToEmbed(left_m, self.get_emojis(), db_context)
        emoji_to_embed[self.right_emoji] = monsterToEmbed(right_m, self.get_emojis(), db_context)

        await self._do_menu(ctx, self.ls_emoji, EmojiUpdater(emoji_to_embed))

    @commands.command(aliases=['lssingle'])
    @checks.bot_has_permissions(embed_links=True)
    async def leaderskillsingle(self, ctx, *, query):
        DGCOG = self.bot.get_cog("Dadguide")
        db_context = DGCOG.database

        m, err, _ = await self.findMonster(query)
        if err:
            await ctx.send(err)
            return
        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.ls_emoji] = monstersToLssEmbed(m)
        emoji_to_embed[self.left_emoji] = monsterToEmbed(m, self.get_emojis(), db_context)

        await self._do_menu(ctx, self.ls_emoji, EmojiUpdater(emoji_to_embed))

    @commands.command(aliases=['helppic', 'helpimg'])
    @checks.bot_has_permissions(embed_links=True)
    async def helpid(self, ctx):
        """Whispers you info on how to craft monster queries for [p]id"""
        await ctx.author.send(box(HELP_MSG.format(ctx)))

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

        m, err, debug_info = await self.findMonster(query)
        if m is not None:
            voice_id = m.voice_id_jp if server == 'jp' else m.voice_id_na
            if voice_id is None:
                await ctx.send(inline("No voice file found for " + m.name_en))
                return
            base_dir = self.settings.voiceDir()
            voice_file = os.path.join(base_dir, server, '{0:03d}.wav'.format(voice_id))
            header = '{} ({})'.format(monsterToHeader(m), server)
            if not os.path.exists(voice_file):
                await ctx.send(inline('Could not find voice for ' + header))
                return
            await ctx.send('Speaking for ' + header)
            await speech_cog.play_path(channel, voice_file)
        else:
            await ctx.send(self.makeFailureMsg(err))

    @commands.group(invoke_without_command=True)
    async def idmode(self, ctx, id_type):
        """Switch between number mode and evo mode

        [p]idmode number
        [p]idmode evo"""
        if id_type in ['evo', 'default']:
            if self.settings.setEvoID(ctx.author.id):
                await ctx.tick()
            else:
                await ctx.send(inline("You're already using evo mode"))
        elif id_type in ['number']:
            if self.settings.rmEvoID(ctx.author.id):
                await ctx.tick()
            else:
                await ctx.send(inline("You're already using number mode"))
        else:
            await ctx.send("id_type must be `number` or `evo`")

    @idmode.command()
    async def survey(self, ctx, value):
        """Change how often you see the id survey

        [p]idmode survey always     (Always see survey after using id)
        [p]idmode survey sometimes  (See survey some of the time after using id)
        [p]idmode survey never      (Never see survey after using id D:)"""
        vals = ['always', 'sometimes', 'never']
        if value in vals:
            await self.config.user(ctx.author).survey_mode.set(vals.index(value))
            await ctx.tick()
        else:
            await ctx.send("value must be `always`, `sometimes`, or `never`")

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
            m1, err1, debug_info1 = await self.findMonster(query)
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

    @staticmethod
    def makeFailureMsg(err):
        msg = ('Lookup failed: {}.\n'
               'Try one of <id>, <name>, [argbld]/[rgbld] <name>. '
               'Unexpected results? Use ^helpid for more info.').format(err)
        return box(msg)

    async def findMonster(self, query, server_filter=ServerFilter.any):
        query = rmdiacritics(query)
        nm, err, debug_info = await self._findMonster(query, server_filter)

        monster_no = nm.monster_id if nm else -1
        self.historic_lookups[query] = monster_no
        json.dump(self.historic_lookups, open(self.historic_lookups_file_path, "w+"))

        m = self.get_monster(nm.monster_id) if nm else None

        return m, err, debug_info

    async def _findMonster(self, query, server_filter=ServerFilter.any):
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
        return await self._findMonster3(query)

    async def _findMonster3(self, query):
        DGCOG = self.bot.get_cog("Dadguide")
        if DGCOG is None:
            raise ValueError("Dadguide cog is not loaded")

        query = rmdiacritics(query).split()
        monstergen = DGCOG.database.get_all_monsters()
        for c, token in enumerate(query):
            try:
                filt = prefix_to_filter(token)
            except:
                print(token)
                raise
            if filt is None:
                monster_name = " ".join(query[c:])
                break
            monstergen = filter(filt, monstergen)
        return max(monstergen, key=lambda x: (not x.is_equip, x.rarity, x.monster_no_na))


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


def monsterToHeader(m: "MonsterModel", link=False, show_types=False, allowed_emojis=None):
    type_emojis = '{} '.format(''.join([str(match_emoji(allowed_emojis, 'mons_type_{}'.format(t.name.lower()))) for t in m.types])) if show_types else ''
    msg = '[{}] {}{}'.format(m.monster_no_na, type_emojis, m.name_en)
    return '[{}]({})'.format(msg, get_pdx_url(m)) if link else msg


def monsterToJaSuffix(m: "MonsterModel", subname_on_override=True):
    suffix = ""
    if m.roma_subname and (subname_on_override or m.name_en_override is None):
        suffix += ' [{}]'.format(m.roma_subname)
    if not m.on_na:
        suffix += ' (JP only)'
    return suffix


def monsterToLongHeader(m: "MonsterModel", link=False, show_types=False, allowed_emojis=None):
    msg = monsterToHeader(m, show_types=show_types, allowed_emojis=allowed_emojis) + monsterToJaSuffix(m)
    return '[{}]({})'.format(msg, get_pdx_url(m)) if link else msg


def monsterToEvoHeader(m: "MonsterModel", emoji_list, link=True):
    prefix = f" {monster_attr_emoji(emoji_list, m)} "
    msg = f"{m.monster_no_na} - {m.name_en}"
    suffix = monsterToJaSuffix(m, False)
    return prefix + ("[{}]({})".format(msg, get_pdx_url(m)) if link else msg) + suffix


def monsterToThumbnailUrl(m: "MonsterModel"):
    return get_portrait_url(m)


def monsterToBaseEmbed(m: "MonsterModel", allowed_emojis):
    header = monsterToLongHeader(m, show_types=True, allowed_emojis=allowed_emojis)
    embed = discord.Embed()
    embed.set_thumbnail(url=monsterToThumbnailUrl(m))
    embed.title = header
    embed.url = get_pdx_url(m)
    embed.set_footer(text='Requester may click the reactions below to switch tabs')
    return embed


def addEvoListFields(monsters, current_monster, emoji_list):
    if not len(monsters):
        return
    field_data = ''
    field_values = []
    for ae in sorted(monsters, key=lambda x: int(x.monster_id)):
        monster_header = monsterToEvoHeader(ae, emoji_list, link=ae.monster_id != current_monster.monster_id) + '\n'
        if len(field_data+monster_header) > 1024:
            field_values.append(field_data)
            field_data = ""
        field_data += monster_header
    field_values.append(field_data)
    return field_values


def monster_attr_emoji(emoji_list, monster: "MonsterModel"):
    attr1 = monster.attr1.name.lower()
    attr2 = monster.attr2.name.lower()
    emoji = "{}_{}".format(attr1, attr2) if attr1 != attr2 else 'orb_{}'.format(attr1)
    return match_emoji(emoji_list, emoji)


def monsterToEvoEmbed(m: "MonsterModel", emoji_list, db_context: "DbContext"):
    embed = monsterToBaseEmbed(m, emoji_list)
    alt_versions = db_context.graph.get_alt_monsters_by_id(m.monster_no)
    gem_versions = list(filter(None, map(db_context.graph.evo_gem_monster, alt_versions)))

    if not len(alt_versions):
        embed.description = 'No alternate evos or evo gem'
        return embed

    evos = addEvoListFields(alt_versions, m, emoji_list)
    if not gem_versions:
        embed.add_field(name="{} alternate evo(s)".format(len(alt_versions)), value=evos[0], inline=False)
        for f in evos[1:]:
            embed.add_field(name="\u200b", value=f)
        return embed
    gems = addEvoListFields(gem_versions, m, emoji_list)

    embed.add_field(name="{} alternate evo(s)".format(len(alt_versions)), value=evos[0], inline=False)
    for e in evos[1:]:
        embed.add_field(name="\u200b", value=e, inline=False)

    embed.add_field(name="{} evolve gem(s)".format(len(gem_versions)), value=gems[0], inline=False)
    for e in gems[1:]:
        embed.add_field(name="\u200b", value=g, inline=False)

    return embed


def addMonsterEvoOfList(monster_id_list, embed, field_name, db_context=None):
    if not len(monster_id_list):
        return
    field_data = ''
    if len(monster_id_list) > 5:
        field_data = '{} monsters'.format(len(monster_id_list))
    else:
        item_count = min(len(monster_id_list), 5)
        monster_list = [db_context.graph.get_monster(m) for m in monster_id_list]
        for ae in sorted(monster_list, key=lambda x: x.monster_no_na, reverse=True)[:item_count]:
            field_data += "{}\n".format(monsterToLongHeader(ae, link=True))
    embed.add_field(name=field_name, value=field_data)


def monsterToEvoMatsEmbed(m: "MonsterModel", db_context: "DbContext", emoji_list):
    embed = monsterToBaseEmbed(m, emoji_list)

    mats_for_evo = db_context.graph.evo_mats_by_monster(m)

    field_name = 'Evo materials'
    field_data = ''
    if len(mats_for_evo) > 0:
        for ae in mats_for_evo:
            field_data += "{}\n".format(monsterToLongHeader(ae, link=True))
    else:
        field_data = 'None'
    embed.add_field(name=field_name, value=field_data)

    addMonsterEvoOfList(db_context.graph.material_of_ids(m), embed, 'Material for', db_context=db_context)
    evo_gem = db_context.graph.evo_gem_monster(m)
    if not evo_gem:
        return embed
    addMonsterEvoOfList(db_context.graph.material_of_ids(evo_gem), embed, "Evo gem is mat for", db_context=db_context)
    return embed


def monsterToPantheonEmbed(m: "MonsterModel", db_context: "DbContext", emoji_list):
    full_pantheon = db_context.get_monsters_by_series(m.series_id)
    pantheon_list = list(filter(lambda x: db_context.graph.monster_is_base(x), full_pantheon))
    if len(pantheon_list) == 0 or len(pantheon_list) > 6:
        return None

    embed = monsterToBaseEmbed(m, emoji_list)

    field_name = 'Pantheon: ' + db_context.graph.get_monster(m.monster_no).series.name
    field_data = ''
    for monster in sorted(pantheon_list, key=lambda x: x.monster_no_na):
        field_data += '\n' + monsterToHeader(monster, link=True)
    embed.add_field(name=field_name, value=field_data)

    return embed


def monsterToSkillupsEmbed(m: "MonsterModel", db_context: "DbContext", emoji_list):
    if m.active_skill is None:
        return None
    possible_skillups_list = db_context.get_monsters_by_active(m.active_skill.active_skill_id)
    skillups_list = list(filter(
        lambda x: db_context.graph.monster_is_farmable_evo(x), possible_skillups_list))

    if len(skillups_list) == 0:
        return None

    embed = monsterToBaseEmbed(m, emoji_list)

    field_name = 'Skillups'
    field_data = ''

    # Prevent huge skillup lists
    if len(skillups_list) > 8:
        field_data = '({} skillups omitted)'.format(len(skillups_list) - 8)
        skillups_list = skillups_list[0:8]

    for monster in sorted(skillups_list, key=lambda x: x.monster_no_na):
        field_data += '\n' + monsterToHeader(monster, link=True)

    if len(field_data.strip()):
        embed.add_field(name=field_name, value=field_data)

    return embed


def monsterToPicUrl(m: "MonsterModel"):
    return get_pic_url(m)


def monsterToPicEmbed(m: "MonsterModel", emoji_list, animated=False):
    embed = monsterToBaseEmbed(m, emoji_list)
    url = monsterToPicUrl(m)
    embed.set_image(url=url)
    # Clear the thumbnail, don't need it on pic
    embed.set_thumbnail(url='')
    extra_links = []
    if animated:
        extra_links.append('Animation: {} -- {}'.format(monsterToVideoUrl(m), monsterToGifUrl(m)))
    if m.orb_skin_id is not None:
        extra_links.append('Orb Skin: {} -- {}'.format(monsterToOrbSkinUrl(m), monsterToOrbSkinCBUrl(m)))
    if len(extra_links) > 0:
        embed.add_field(name='Extra Links', value='\n'.join(extra_links))

    return embed


def monsterToVideoUrl(m: "MonsterModel", link_text='(MP4)'):
    return '[{}]({})'.format(link_text, VIDEO_TEMPLATE.format(m.monster_no_jp))


def monsterToGifUrl(m: "MonsterModel", link_text='(GIF)'):
    return '[{}]({})'.format(link_text, GIF_TEMPLATE.format(m.monster_no_jp))


def monsterToOrbSkinUrl(m: "MonsterModel", link_text='Regular'):
    return '[{}]({})'.format(link_text, ORB_SKIN_TEMPLATE.format(m.orb_skin_id))


def monsterToOrbSkinCBUrl(m: "MonsterModel", link_text='Color Blind'):
    return '[{}]({})'.format(link_text, ORB_SKIN_CB_TEMPLATE.format(m.orb_skin_id))


def monstersToLsEmbed(left_m: "MonsterModel", right_m: "MonsterModel"):
    lls = left_m.leader_skill
    rls = right_m.leader_skill

    multiplier_text = createMultiplierText(lls, rls)

    embed = discord.Embed()
    embed.title = '{}\n\n'.format(multiplier_text)
    description = ''
    description += '\n**{}**\n{}'.format(
        monsterToHeader(left_m, link=True),
        lls.desc if lls else 'None')
    description += '\n**{}**\n{}'.format(
        monsterToHeader(right_m, link=True),
        rls.desc if rls else 'None')
    embed.description = description

    return embed


def monstersToLssEmbed(m: "MonsterModel"):
    multiplier_text = createSingleMultiplierText(m.leader_skill)

    embed = discord.Embed()
    embed.title = '{}\n\n'.format(multiplier_text)
    description = ''
    description += '\n**{}**\n{}'.format(
        monsterToHeader(m, link=True),
        m.leader_skill.desc if m.leader_skill else 'None')
    embed.description = description

    return embed


def monsterToHeaderEmbed(m: "MonsterModel", allowed_emojis):
    header = monsterToLongHeader(m, link=True, show_types=True, allowed_emojis=allowed_emojis)
    embed = discord.Embed()
    embed.description = header
    return embed


def monsterToAcquireString(m: "MonsterModel", db_context: "DbContext"):
    acquire_text = None
    if db_context.graph.monster_is_farmable(m) and not db_context.graph.monster_is_mp_evo(m):
        # Some MP shop monsters 'drop' in PADR
        acquire_text = 'Farmable'
    elif db_context.graph.monster_is_farmable_evo(m) and not db_context.graph.monster_is_mp_evo(m):
        acquire_text = 'Farmable Evo'
    elif m.in_pem:
        acquire_text = 'In PEM'
    elif db_context.graph.monster_is_pem_evo(m):
        acquire_text = 'PEM Evo'
    elif m.in_rem:
        acquire_text = 'In REM'
    elif db_context.graph.monster_is_rem_evo(m):
        acquire_text = 'REM Evo'
    elif m.in_mpshop:
        acquire_text = 'MP Shop'
    elif db_context.graph.monster_is_mp_evo(m):
        acquire_text = 'MP Shop Evo'
    return acquire_text


def match_emoji(emoji_list, name):
    for e in emoji_list:
        if e.name == name:
            return e
    return name


def monsterToEmbed(m: "MonsterModel", emoji_list, db_context: "DbContext"):
    embed = monsterToBaseEmbed(m, emoji_list)

    info_row_1 = 'Inheritable' if m.is_inheritable else 'Not inheritable'
    acquire_text = monsterToAcquireString(m, db_context)
    tet_text = db_context.graph.true_evo_type_by_monster(m).value

    orb_skin = "" if m.orb_skin_id is None else " (Orb Skin)"

    info_row_2 = '**Rarity** {} (**Base** {}){}\n**Cost** {}'.format(
        m.rarity,
        db_context.graph.get_base_monster_by_id(m.monster_no).rarity,
        orb_skin,
        m.cost
    )

    if acquire_text:
        info_row_2 += '\n**{}**'.format(acquire_text)
    if tet_text in ("Reincarnated", "Assist", "Pixel", "Super Reincarnated"):
        info_row_2 += '\n**{}**'.format(tet_text)

    embed.add_field(name=info_row_1, value=info_row_2)

    hp, atk, rcv, weighted = m.stats()
    if m.limit_mult > 0:
        lb_hp, lb_atk, lb_rcv, lb_weighted = m.stats(lv=110)
        stats_row_1 = 'Weighted {} | LB {} (+{}%)'.format(weighted, lb_weighted, m.limit_mult)
        stats_row_2 = '**HP** {} ({})\n**ATK** {} ({})\n**RCV** {} ({})'.format(
            hp, lb_hp, atk, lb_atk, rcv, lb_rcv)
    else:
        stats_row_1 = 'Weighted {}'.format(weighted)
        stats_row_2 = '**HP** {}\n**ATK** {}\n**RCV** {}'.format(hp, atk, rcv)
    embed.add_field(name=stats_row_1, value=stats_row_2)

    awakenings_row = ''
    for idx, a in enumerate(m.awakenings):
        as_id = a.awoken_skill_id
        as_name = a.name
        mapped_awakening = AWAKENING_MAP.get(as_id, as_name)
        mapped_awakening = match_emoji(emoji_list, mapped_awakening)

        # Wrap superawakenings to the next line
        if len(m.awakenings) - idx == m.superawakening_count:
            awakenings_row += '\n{}'.format(mapped_awakening)
        else:
            awakenings_row += ' {}'.format(mapped_awakening)

    awakenings_row = awakenings_row.strip()

    if not len(awakenings_row):
        awakenings_row = 'No Awakenings'

    if db_context.graph.monster_is_transform_base(m):
        killers_row = '**Available killers:** [{} slots] {}'.format(m.latent_slots, ' '.join(m.killers))
    else:
        base_transform = db_context.graph.get_transform_base_by_id(m.monster_id)
        killers_row = '**Avail. killers (pre-transform):** [{} slots] {}'.format(base_transform.latent_slots, ' '.join(base_transform.killers))

    embed.description = '{}\n{}'.format(awakenings_row, killers_row)

    active_header = 'Active Skill'
    active_body = 'None'
    active_skill = m.active_skill
    if active_skill:
        active_header = 'Active Skill ({} -> {})'.format(active_skill.turn_max,
                                                         active_skill.turn_min)
        active_body = active_skill.desc
    embed.add_field(name=active_header, value=active_body, inline=False)

    leader_skill = m.leader_skill
    ls_row = m.leader_skill.desc if leader_skill else 'None'
    ls_header = 'Leader Skill'
    if leader_skill:
        multiplier_text = createMultiplierText(leader_skill)
        ls_header += " {}".format(multiplier_text)
    embed.add_field(name=ls_header, value=ls_row, inline=False)

    evos_header = "Alternate Evos"
    evos_body = ", ".join(f"**{m2.monster_id}**"
                          if m2.monster_id == m.monster_id
                          else f"[{m2.monster_id}]({get_pdx_url(m2)})"
                          for m2 in
                          sorted({*db_context.graph.get_alt_monsters_by_id(m.monster_no)}, key=lambda x: x.monster_id))
    embed.add_field(name=evos_header, value=evos_body, inline=False)

    return embed


def monsterToOtherInfoEmbed(m: "MonsterModel", db_context: "DbContext", emoji_list):
    embed = monsterToBaseEmbed(m, emoji_list)
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

    body_text += '\n**Series:** {}'.format(db_context.graph.get_monster(m.monster_no).series.name)
    body_text += '\n**Sell MP:** {:,}'.format(m.sell_mp)
    if m.buy_mp is not None:
        body_text += "  **Buy MP:** {:,}".format(m.buy_mp)

    if m.exp < 1000000:
        xp_text = '{:,}'.format(m.exp)
    else:
        xp_text = '{:.1f}'.format(m.exp / 1000000).rstrip('0').rstrip('.') + 'M'
    body_text += '\n**XP to Max:** {}'.format(xp_text)
    body_text += '  **Max Level:**: {}'.format(m.level)
    body_text += '\n**Fodder EXP:** {:,}'.format(m.fodder_exp)
    body_text += '\n**Rarity:** {} **Cost:** {}'.format(m.rarity, m.cost)

    embed.description = body_text

    return embed


AWAKENING_MAP = {
    1: 'boost_hp',
    2: 'boost_atk',
    3: 'boost_rcv',
    4: 'reduce_fire',
    5: 'reduce_water',
    6: 'reduce_wood',
    7: 'reduce_light',
    8: 'reduce_dark',
    9: 'misc_autoheal',
    10: 'res_bind',
    11: 'res_blind',
    12: 'res_jammer',
    13: 'res_poison',
    14: 'oe_fire',
    15: 'oe_water',
    16: 'oe_wood',
    17: 'oe_light',
    18: 'oe_dark',
    19: 'misc_te',
    20: 'misc_bindclear',
    21: 'misc_sb',
    22: 'row_fire',
    23: 'row_water',
    24: 'row_wood',
    25: 'row_light',
    26: 'row_dark',
    27: 'misc_tpa',
    28: 'res_skillbind',
    29: 'oe_heart',
    30: 'misc_multiboost',
    31: 'killer_dragon',
    32: 'killer_god',
    33: 'killer_devil',
    34: 'killer_machine',
    35: 'killer_balance',
    36: 'killer_attacker',
    37: 'killer_physical',
    38: 'killer_healer',
    39: 'killer_evomat',
    40: 'killer_awoken',
    41: 'killer_enhancemat',
    42: 'killer_vendor',
    43: 'misc_comboboost',
    44: 'misc_guardbreak',
    45: 'misc_extraattack',
    46: 'teamboost_hp',
    47: 'teamboost_rcv',
    48: 'misc_voidshield',
    49: 'misc_assist',
    50: 'misc_super_extraattack',
    51: 'misc_skillcharge',
    52: 'res_bind_super',
    53: 'misc_te_super',
    54: 'res_cloud',
    55: 'res_seal',
    56: 'misc_sb_super',
    57: 'attack_boost_high',
    58: 'attack_boost_low',
    59: 'l_shield',
    60: 'l_attack',
    61: 'misc_super_comboboost',
    62: 'orb_combo',
    63: 'misc_voice',
    64: 'misc_dungeonbonus',
    65: 'reduce_hp',
    66: 'reduce_atk',
    67: 'reduce_rcv',
    68: 'res_blind_super',
    69: 'res_jammer_super',
    70: 'res_poison_super',
    71: 'misc_jammerboost',
    72: 'misc_poisonboost',
}

def humanize_number(number, sigfigs=2):
    n = float("{0:.{1}g}".format(number, sigfigs))
    if n >= 1e9:
        return str(int(n//1e9))+"B"
    elif n >= 1e6:
        return str(int(n//1e6))+"M"
    elif n >= 1e3:
        return str(int(n//1e3))+"k"
    else:
        return str(int(n))

def createMultiplierText(ls1, ls2=None):
    if ls2 and not ls1:
        ls1, ls2 = ls2, ls1

    if ls1:
        hp1, atk1, rcv1, resist1, combo1, fua1, mfua1, te1 = ls1.data
    else:
        hp1, atk1, rcv1, resist1, combo1, fua1, mfua1, te1 = 1, 1, 1, 0, 0, 0, 0, 0

    if ls2:
        hp2, atk2, rcv2, resist2, combo2, fua2, mfua2, te2 = ls2.data
    else:
        hp2, atk2, rcv2, resist2, combo2, fua2, mfua2, te2 = hp1, atk1, rcv1, resist1, combo1, fua1, mfua1, te1

    return format_ls_text(
            hp1*hp2,
            atk1*atk2,
            rcv1*rcv2,
            1 - (1 - resist1) * (1 - resist2),
            combo1+combo2,
            fua1+fua2,
            mfua1+mfua2,
            te1+te2
           )


def createSingleMultiplierText(ls=None):
    if ls:
        hp, atk, rcv, resist, combo, fua, mfua, te = ls.data
    else:
        hp, atk, rcv, resist, combo, fua, mfua, te = 1, 1, 1, 0, 0, 0, 0, 0

    return format_ls_text(hp, atk, rcv, resist, combo, fua, mfua, te)


def format_ls_text(hp, atk, rcv, resist=0, combo=0, fua=0, mfua=0, te=0):
    def fmtNum(val):
        return '{:.2f}'.format(val).strip('0').rstrip('.')

    text = "{}/{}/{}".format(fmtNum(hp), fmtNum(atk), fmtNum(rcv))
    if resist != 0:
        text += ' Resist {}%'.format(fmtNum(100 * resist))

    extras = []
    if combo:
        extras.append('+{}c'.format(combo))
    if fua:
        extras.append('{} fua'.format(humanize_number(fua, 2)))
    elif mfua:
        extras.append('fua')

    if extras:
        return '[{}] [{}]'.format(text, ' '.join(extras))
    return '[{}]'.format(text)
