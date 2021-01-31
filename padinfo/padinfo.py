import asyncio
import json
import logging
import os
import random
import re
import urllib.parse
from collections import OrderedDict
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING

import discord
import tsutils
from Levenshtein import jaro_winkler
from discord import Color
from discordmenu.emoji_cache import emoji_cache
from discordmenu.intra_message_state import IntraMessageState
from redbot.core import checks, commands, data_manager, Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, inline, bold, pagify, text_to_file
from tabulate import tabulate
from tsutils import EmojiUpdater, Menu, char_to_emoji, is_donor

from padinfo.common.config import BotConfig
from padinfo.common.emoji_map import get_attribute_emoji_by_enum, get_awakening_emoji, get_type_emoji
from padinfo.core import find_monster as fm
from padinfo.core.button_info import button_info
from padinfo.core.find_monster import find_monster, findMonster1, findMonster3, \
    findMonsterCustom2, findMonsterCustom
from padinfo.emojiupdaters import IdEmojiUpdater, ScrollEmojiUpdater
from padinfo.core.historic_lookups import historic_lookups
from padinfo.id_menu import IdMenu
from padinfo.ls_menu import LeaderSkillMenu
from padinfo.core.padinfo_settings import settings
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view_state.leader_skill import LeaderSkillViewState

if TYPE_CHECKING:
    pass

logger = logging.getLogger('red.padbot-cogs.padinfo')

EMBED_NOT_GENERATED = -1

IDGUIDE = "https://github.com/TsubakiBotPad/pad-cogs/wiki/%5Eid-user-guide"


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


class PadInfo(commands.Cog):
    """Info for PAD Cards"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.menu = Menu(bot)

        # These emojis are the keys into the idmenu submenus
        self.id_emoji = '\N{HOUSE BUILDING}'
        self.evo_emoji = char_to_emoji('e')
        self.mats_emoji = '\N{MEAT ON BONE}'
        self.ls_emoji = '\N{HOUSE BUILDING}'
        self.left_emoji = char_to_emoji('l')
        self.right_emoji = char_to_emoji('r')
        self.pantheon_emoji = '\N{CLASSICAL BUILDING}'
        self.pic_emoji = '\N{FRAME WITH PICTURE}'
        self.other_info_emoji = '\N{SCROLL}'
        self.first_monster_emoji = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
        self.previous_monster_emoji = '\N{BLACK LEFT-POINTING TRIANGLE}'
        self.next_monster_emoji = '\N{BLACK RIGHT-POINTING TRIANGLE}'
        self.last_monster_emoji = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'
        self.transform_emoji = '\N{HOUSE BUILDING}'
        self.tfid_emoji = '\N{SQUARED ID}'
        self.remove_emoji = self.menu.emoji['no']

        self.config = Config.get_conf(self, identifier=9401770)
        self.config.register_user(survey_mode=0, color=None, beta_id3=False, lastaction=None)
        self.config.register_global(sometimes_perc=20, good=0, bad=0, do_survey=False, test_suite={}, fluff_suite=[])

        self.fm1 = fm.findMonster1
        self.fm_ = fm._findMonster

    def cog_unload(self):
        """Manually nulling out database because the GC for cogs seems to be pretty shitty"""
        # TODO.... manage historic_lookups??? probably not.

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
                emoji_cache.set_guild_ids([g.id for g in self.bot.guilds])
                emoji_cache.refresh_from_discord_bot(self.bot)
                dg_cog = self.bot.get_cog('Dadguide')
                await dg_cog.wait_until_ready()
            except Exception as ex:
                wait_time = 5
                logger.exception("reload padinfo loop caught exception " + str(ex))

            await asyncio.sleep(wait_time)

    def get_monster(self, monster_id: int):
        dg_cog = self.bot.get_cog('Dadguide')
        return dg_cog.get_monster(monster_id)

    @commands.Cog.listener('on_raw_reaction_add')
    async def test_reaction_add(self, event):
        channel = self.bot.get_channel(event.channel_id)
        try:
            message = await channel.fetch_message(event.message_id)
        except discord.errors.NotFound:
            return

        ims = IntraMessageState.extract_data(message.embeds[0])
        if not ims:
            return

        emoji_obj = event.emoji
        if isinstance(emoji_obj, str):
            emoji_clicked = emoji_obj
        else:
            emoji_clicked = event.emoji.name

        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        if menu_type == LeaderSkillMenu.MENU_TYPE:
            embed_menu = LeaderSkillMenu.menu(original_author_id)
            if not (await embed_menu.should_respond(message, event)):
                return

            dgcog = await self.get_dgcog()
            user_config = await BotConfig.get_user(self.config, original_author_id)
            data = {
                'dgcog': dgcog,
                'user_config': user_config
            }
            await embed_menu.transition(message, ims, emoji_clicked, **data)

    @commands.command()
    async def jpname(self, ctx, *, query: str):
        """Show the Japanese name of a monster"""
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
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
        await self._do_id3(ctx, "inna " + query)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def idjp(self, ctx, *, query: str):
        """Monster info (limited to JP monsters ONLY)"""
        await self._do_id3(ctx, "injp " + query)

    async def get_dgcog(self):
        dgcog = self.bot.get_cog("Dadguide")
        if dgcog is None:
            raise ValueError("Dadguide cog is not loaded")
        await dgcog.wait_until_ready()
        return dgcog

    async def _do_id(self, ctx, query: str):
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonster1(dgcog, query)

        if m is not None:
            await self._do_idmenu(ctx, m, self.id_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    async def send_survey_after(self, ctx, query, result_monster):
        dgcog = await self.get_dgcog()
        sm = await self.config.user(ctx.author).survey_mode()
        sms = [1, await self.config.sometimes_perc() / 100, 0][sm]
        if random.random() < sms:
            m1, _, _ = await findMonster1(dgcog, query)
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
    @checks.bot_has_permissions()
    async def id2(self, ctx, *, query: str):
        """Monster info (main tab)"""
        await ctx.send("id2 has been discontinued!  For an even better searching experience,"
                       " opt into the id3 beta using `{}idset beta y`".format(ctx.prefix))

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def id3(self, ctx, *, query: str):
        """Monster info (main tab)"""
        await self._do_id3(ctx, query)

    async def _do_id3(self, ctx, query):
        dgcog = await self.get_dgcog()
        m = await findMonster3(dgcog, query)
        if m and m.monster_no_na != m.monster_no_jp:
            await ctx.send("The NA ID and JP ID of this card differ! "
                           "The JP ID is 1053 you can query with {0.prefix}id jp1053.".format(ctx) +
                           (" Make sure you use the **JP id number** when updating the Google doc!!!!!" if
                            ctx.author.id in self.bot.get_cog("PadGlobal").settings.bot_settings['admins'] else ""))
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
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.evo_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command(name="mats", aliases=['evomats', 'evomat', 'skillups'])
    @checks.bot_has_permissions(embed_links=True)
    async def evomats(self, ctx, *, query: str):
        """Monster info (evo materials tab)"""
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
        if m is not None:
            menu = await self._do_idmenu(ctx, m, self.mats_emoji)
            if menu == EMBED_NOT_GENERATED:
                await ctx.send(inline("This monster has no mats or skillups and isn't used in any evolutions"))
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command(aliases=["series"])
    @checks.bot_has_permissions(embed_links=True)
    async def pantheon(self, ctx, *, query: str):
        """Monster info (pantheon tab)"""
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
        if m is not None:
            menu = await self._do_idmenu(ctx, m, self.pantheon_emoji)
            if menu == EMBED_NOT_GENERATED:
                await ctx.send(inline('Not a pantheon monster'))
        else:
            await self.makeFailureMsg(ctx, query, err)

    async def _do_idmenu(self, ctx, m, starting_menu_emoji):
        DGCOG = self.bot.get_cog("Dadguide")
        db_context = DGCOG.database

        alt_versions = db_context.graph.get_alt_monsters_by_id(m.monster_id)
        emoji_to_embed = await self.get_id_emoji_options(ctx,
                                                         m=m, scroll=sorted({*alt_versions}, key=lambda
                x: x.monster_id) if settings.checkEvoID(
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

        id_embed = await menu.make_id_embed(m)
        evo_embed = await menu.make_evo_embed(m)
        mats_embed = await menu.make_evo_mats_embed(m)
        pic_embed = await menu.make_picture_embed(m)
        other_info_embed = await menu.make_otherinfo_embed(m)
        pantheon_embed = await menu.make_pantheon_embed(m)

        emoji_to_embed = OrderedDict()

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

        emoji_to_embed[self.id_emoji] = id_embed
        emoji_to_embed[self.evo_emoji] = evo_embed
        if mats_embed:
            emoji_to_embed[self.mats_emoji] = mats_embed
        emoji_to_embed[self.pic_emoji] = pic_embed
        if pantheon_embed:
            emoji_to_embed[self.pantheon_emoji] = pantheon_embed

        emoji_to_embed[self.other_info_emoji] = other_info_embed

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
            emoji_to_embed[emoji] = await menu.make_id_embed(m)
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
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.pic_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def links(self, ctx, *, query: str):
        """Monster links"""
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
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
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
        if m is not None:
            await self._do_idmenu(ctx, m, self.other_info_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def buttoninfo(self, ctx, *, query: str):
        """Button farming theorycrafting info"""
        dgcog = await self.get_dgcog()
        monster, err, _ = await findMonsterCustom(dgcog, ctx, self.config, query)
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
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
        if m is not None:
            menu = IdMenu(ctx, allowed_emojis=self.get_emojis())
            embed = await menu.make_lookup_embed(m)
            await ctx.send(embed=embed)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def evolist(self, ctx, *, query):
        """Monster info (for all monsters in the evo tree)"""
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
        if m is not None:
            await self._do_evolistmenu(ctx, m)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command(aliases=['collabscroll'])
    @checks.bot_has_permissions(embed_links=True)
    async def seriesscroll(self, ctx, *, query: str):
        """Scroll through the monsters in a collab"""
        dgcog = self.bot.get_cog("Dadguide")
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
        ms = dgcog.database.get_monsters_by_series(m.series.series_id)

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
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)

        if m is not None:
            await self._do_scrollmenu(ctx, m,
                                      sorted(dgcog.database.graph.get_alt_monsters(m), key=lambda x: x.monster_id),
                                      self.id_emoji)
        else:
            await self.makeFailureMsg(ctx, query, err)

    @commands.command(aliases=['leaders', 'leaderskills', 'ls'], usage="<card_1> [card_2]")
    @checks.bot_has_permissions(embed_links=True)
    async def leaderskill(self, ctx, *, raw_query):
        """Display the multiplier and leaderskills for two monsters

        Gets two monsters separated by a slash, wrapping quotes, a comma,
        or spaces (if there's only two words).
        [p]ls r sonia/ revo lu bu
        [p]ls r sonia "revo lu bu"
        [p]ls sonia lubu
        """
        beta_id3 = await self.config.user(ctx.author).beta_id3()
        dgcog = await self.get_dgcog()
        l_err, l_mon, l_query, r_err, r_mon, r_query = await self.leaderskill_perform_query(dgcog, raw_query, beta_id3)

        err_msg = '{} query failed to match a monster: [ {} ]. If your query is multiple words, try separating the queries with / or wrap with quotes.'
        if l_err:
            await ctx.send(inline(err_msg.format('Left', l_query)))
            return
        if r_err:
            await ctx.send(inline(err_msg.format('Right', r_query)))
            return

        color = await self.get_user_embed_color(ctx)
        original_author_id = ctx.message.author.id
        state = LeaderSkillViewState(original_author_id, LeaderSkillMenu.MENU_TYPE, raw_query, color, l_mon, r_mon,
                                     l_query, r_query)
        menu = LeaderSkillMenu.menu(original_author_id)
        await menu.create(ctx, state)

    async def leaderskill_perform_query(self, dgcog, raw_query, beta_id3):
        # Remove unicode quotation marks
        query = re.sub("[\u201c\u201d]", '"', raw_query)

        # deliberate order in case of multiple different separators.
        for sep in ('"', '/', ',', ' '):
            if sep in query:

                left_query, *right_query = [x.strip() for x in query.split(sep) if x.strip()] or (
                    '', '')  # or in case of ^ls [sep] which is empty list
                # split on first separator, with if x.strip() block to prevent null values from showing up, mainly for quotes support
                # right query is the rest of query but in list form because of how .strip() works. bring it back to string form with ' '.join
                right_query = ' '.join(q for q in right_query)
                if sep == ' ':
                    # Handle a very specific failure case, user typing something like "uuvo ragdra"
                    nm, err, debug_info = dgcog.index.find_monster(query)
                    if not err and left_query in nm.prefixes:
                        left_query = query
                        right_query = None

                break

        else:  # no separators
            left_query, right_query = query, None
        left_m, left_err, _ = await findMonsterCustom2(dgcog, beta_id3, left_query)
        if right_query:
            right_m, right_err, _ = await findMonsterCustom2(dgcog, beta_id3, right_query)
        else:
            right_m, right_err, = left_m, left_err
        return left_err, left_m, left_query, right_err, right_m, right_query

    async def get_user_embed_color(self, ctx):
        color = await self.config.user(ctx.author).color()
        return self.user_color_to_discord_color(color)

    def user_color_to_discord_color(self, color):
        if color is None:
            return Color.default()
        elif color == "random":
            return Color(random.randint(0x000000, 0xffffff))
        else:
            return discord.Color(color)

    @commands.command(aliases=['lssingle'])
    @checks.bot_has_permissions(embed_links=True)
    async def leaderskillsingle(self, ctx, *, query):
        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
        if err:
            await ctx.send(err)
            return
        menu = IdMenu(ctx, db_context=dgcog.database, allowed_emojis=self.get_emojis())
        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.ls_emoji] = await menu.make_lssingle_embed(m)
        emoji_to_embed[self.left_emoji] = await menu.make_id_embed(m)

        await self._do_menu(ctx, self.ls_emoji, EmojiUpdater(emoji_to_embed))

    @commands.command(aliases=['tfinfo'])
    @checks.bot_has_permissions(embed_links=True)
    async def transforminfo(self, ctx, *, query):
        DGCOG = self.bot.get_cog("Dadguide")
        db_context = DGCOG.database
        # prepend transformbase modifier
        m, err, _ = await self.findMonsterCustom(ctx, query)
        if err:
            await ctx.send(err)
            return

        menu = IdMenu(ctx, db_context=db_context, allowed_emojis=self.get_emojis())
        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.transform_emoji] = await menu.make_transforminfo_embed(m)
        # base and transform
        emoji_to_embed[self.tfid_emoji] = await menu.make_id_embed(m)

        await self._do_menu(ctx, self.transform_emoji, EmojiUpdater(emoji_to_embed))

    @commands.group()
    # @checks.is_owner()
    async def idtest(self, ctx):
        """ID Test suite subcommands"""

    @idtest.command(name="add")
    async def idt_add(self, ctx, id: int, *, query):
        """Add a test for the id3 test suite (Append `| reason` to add a reason)"""
        query, *reason = query.split("|")
        query = query.strip()
        if await self.config.user(ctx.author).lastaction() != 'id3' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to add to the id3 test suite?"):
            return
        await self.config.user(ctx.author).lastaction.set('id3')

        async with self.config.test_suite() as suite:
            oldd = suite.get(query, {})
            if oldd.get('result') == id:
                await ctx.send(f"This test case already exists with id `{sorted(suite).index(query)}`.")
                return
            suite[query] = {
                'result': id,
                'ts': datetime.now().timestamp(),
                'reason': reason[0].strip() if reason else ''
            }

            if await tsutils.get_reaction(ctx, f"Added with id `{sorted(suite).index(query)}`",
                                          "\N{LEFTWARDS ARROW WITH HOOK}"):
                if oldd:
                    suite[query] = oldd
                else:
                    del suite[query]
                await ctx.react_quietly("\N{CROSS MARK}")
            else:
                await ctx.send(f"Successfully added test case with id `{sorted(suite).index(query)}`")
                await ctx.tick()

    @idtest.group(name="name")
    async def idt_name(self, ctx):
        """Name subcommands"""

    @idtest.group(name="fluff")
    async def idt_fluff(self, ctx):
        """Fluff subcommands"""

    @idt_name.command(name="add")
    async def idtn_add(self, ctx, id: int, token, *, reason=""):
        """Add a name token test to the id3 test suite"""
        await self.norf_add(ctx, id, token, reason, False)

    @idt_fluff.command(name="add")
    async def idtf_add(self, ctx, id: int, token, *, reason=""):
        """Add a fluff token test to the id3 test suite"""
        await self.norf_add(ctx, id, token, reason, True)

    async def norf_add(self, ctx, id: int, token, reason, fluffy):
        reason = reason.lstrip("| ")
        if await self.config.user(ctx.author).lastaction() != 'name' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to add to the fluff/name test suite?"):
            return
        await self.config.user(ctx.author).lastaction.set('name')

        async with self.config.fluff_suite() as suite:
            if any(t['id'] == id and t['token'] == token and t['fluff'] == fluffy for t in suite):
                await ctx.send("This test already exists.")
                return

            old = None
            if any(t['id'] == id and t['token'] == token for t in suite):
                old = [t for t in suite if t['id'] == id and t['token'] == token][0]
                if not await tsutils.confirm_message(ctx, f"Are you sure you want to change"
                                                          f" the type of test case #{suite.index(old)}"
                                                          f" `{id} - {token}` from "
                                                          f" **{'fluff' if fluffy else 'name'}** to"
                                                          f" **{'name' if fluffy else 'fluff'}**?"):
                    await ctx.react_quietly("\N{CROSS MARK}")
                    return
                suite.remove(old)

            case = {
                'id': id,
                'token': token,
                'fluff': fluffy,
                'reason': reason,
                'ts': datetime.now().timestamp()
            }

            suite.append(case)
            suite.sort(key=lambda v: (v['id'], v['token'], v['fluff']))

            if await tsutils.get_reaction(ctx, f"Added with id `{suite.index(case)}`", "\N{LEFTWARDS ARROW WITH HOOK}"):
                suite.pop()
                if old:
                    suite.append(old)
                await ctx.react_quietly("\N{CROSS MARK}")
            else:
                m = await ctx.send(f"Successfully added new case with id `{suite.index(case)}`")
                await m.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @idtest.command(name="import")
    async def idt_import(self, ctx, *, queries):
        """Import id3 tests"""
        if await self.config.user(ctx.author).lastaction() != 'id3' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **query**?"):
            return
        await self.config.user(ctx.author).lastaction.set('id3')

        cases = re.findall(r'\s*(?:\d+. )?(.+?) + - (\d+) *(.*)', queries)
        async with self.config.test_suite() as suite:
            for query, result, reason in cases:
                suite[query] = {'result': int(result), 'reason': reason, 'ts': datetime.now().timestamp()}
        await ctx.tick()

    @idt_name.command(name="import")
    async def idtn_import(self, ctx, *, queries):
        """Import name/fluff tests"""
        await self.norf_import(ctx, id, queries)

    @idt_fluff.command(name="import")
    async def idtf_import(self, ctx, *, queries):
        """Import name/fluff tests"""
        await self.norf_import(ctx, id, queries)

    async def norf_import(self, ctx, queries):
        if await self.config.user(ctx.author).lastaction() != 'name' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **name/fluff**?"):
            return
        await self.config.user(ctx.author).lastaction.set('name')

        cases = re.findall(r'\s*(?:\d+. )?(.+?) + - (\d+)\s+(\w*) *(.*)', queries)
        async with self.config.fluff_suite() as suite:
            for query, result, fluff, reason in cases:
                print(query, result, fluff, reason)
                if not any(c['id'] == int(result) and c['token'] == query for c in suite):
                    suite.append({
                        'id': int(result),
                        'token': query,
                        'fluff': fluff == 'fluff',
                        'reason': reason,
                        'ts': datetime.now().timestamp()})
        await ctx.tick()

    @idtest.command(name="remove", aliases=["delete", "rm"])
    async def idt_remove(self, ctx, *, item):
        """Remove an id3 test"""
        if await self.config.user(ctx.author).lastaction() != 'id3' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **query**?"):
            return
        await self.config.user(ctx.author).lastaction.set('id3')

        async with self.config.test_suite() as suite:
            if item in suite:
                del suite[item]
            elif item.isdigit() and int(item) < len(suite):
                del suite[sorted(suite)[int(item)]]
            else:
                await ctx.react_quietly("\N{CROSS MARK}")
                return
        await ctx.tick()

    @idt_name.command(name="remove")
    async def idtn_remove(self, ctx, *, item: int):
        """Remove a name/fluff test"""
        await self.norf_remove(ctx, item)

    @idt_fluff.command(name="remove")
    async def idtf_remove(self, ctx, *, item: int):
        """Remove a name/fluff test"""
        await self.norf_remove(ctx, item)

    async def norf_remove(self, ctx, item):
        if await self.config.user(ctx.author).lastaction() != 'name' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **name/fluff**?"):
            return
        await self.config.user(ctx.author).lastaction.set('name')

        async with self.config.fluff_suite() as suite:
            if item >= len(suite):
                await ctx.send("There are not that many items.")
                return
            suite.remove(sorted(suite, key=lambda v: (v['id'], v['token'], v['fluff']))[item])
        await ctx.tick()

    @idtest.command(name="setreason", aliases=["addreason"])
    async def idt_setreason(self, ctx, number: int, *, reason):
        """Set a reason for an id3 test case"""
        if reason == '""':
            reason = ""
        if await self.config.user(ctx.author).lastaction() != 'id3' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **query**?"):
            return
        await self.config.user(ctx.author).lastaction.set('id3')

        async with self.config.test_suite() as suite:
            if number >= len(suite):
                await ctx.react_quietly("\N{CROSS MARK}")
                return
            suite[sorted(suite)[number]]['reason'] = reason
        await ctx.tick()

    @idt_name.command(name="setreason")
    async def idtn_setreason(self, ctx, number: int, *, reason):
        """Set a reason for an name/fluff test case"""
        await self.norf_setreason(ctx, number, reason)

    @idt_fluff.command(name="setreason")
    async def idtf_setreason(self, ctx, number: int, *, reason):
        """Set a reason for an name/fluff test case"""
        await self.norf_setreason(ctx, number, reason)

    async def norf_setreason(self, ctx, number, reason):
        if reason == '""':
            reason = ""
        if await self.config.user(ctx.author).lastaction() != 'name' and \
                not await tsutils.confirm_message(ctx, "Are you sure you want to edit **name/fluff**?"):
            return
        await self.config.user(ctx.author).lastaction.set('name')

        async with self.config.fluff_suite() as suite:
            if number >= len(suite):
                await ctx.react_quietly("\N{CROSS MARK}")
                return
            sorted(suite, key=lambda v: (v['id'], v['token'], v['fluff']))[number]['reason'] = reason
        await ctx.tick()

    @idtest.command(name="list")
    async def idt_list(self, ctx):
        """List id3 tests"""
        await self.config.user(ctx.author).lastaction.set('id3')

        suite = await self.config.test_suite()
        o = ""
        ml = len(max(suite, key=len))
        for c, kv in enumerate(sorted(suite.items())):
            o += f"{str(c).rjust(3)}. {kv[0].ljust(ml)} - {str(kv[1]['result']).ljust(4)}\t{kv[1].get('reason') or ''}\n"
        if not o:
            await ctx.send("There are no test cases.")
        for page in pagify(o):
            await ctx.send(box(page))

    @idt_name.command(name="list")
    async def idtn_list(self, ctx, inclusive: bool = False):
        """List name tests"""
        await self.norf_list(ctx, False, inclusive)

    @idt_fluff.command(name="list")
    async def idtf_list(self, ctx, inclusive: bool = False):
        """List fluff tests"""
        await self.norf_list(ctx, True, inclusive)

    async def norf_list(self, ctx, fluff, inclusive):
        """List name/fluff tests"""
        await self.config.user(ctx.author).lastaction.set('name')

        suite = await self.config.fluff_suite()
        o = ""
        for c, v in enumerate(sorted(suite, key=lambda v: (v['id'], v['token'], v['fluff']))):
            if inclusive or v['fluff'] == fluff:
                o += f"{str(c).rjust(3)}. {v['token'].ljust(10)} - {str(v['id']).ljust(4)}" \
                     f"\t{'fluff' if v['fluff'] else 'name '}\t{v.get('reason', '')}\n"
        if not o:
            await ctx.send("There are no test cases.")
        for page in pagify(o):
            await ctx.send(box(page))

    @idtest.command(name="listrecent")
    async def idt_listrecent(self, ctx, count: int = 0):
        """List recent id3 tests"""
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
        """Run all id3 tests"""
        suite = await self.config.test_suite()
        dgcog = await self.get_dgcog()
        await self.config.user(ctx.author).lastaction.set('id3')
        c = 0
        o = ""
        ml = len(max(suite, key=len)) + 2
        rcircle = '\N{LARGE RED CIRCLE}'
        async with ctx.typing():
            for q, r in suite.items():
                m = await findMonster3(dgcog, q)
                mid = m and m.monster_id
                if m is not None and m.monster_id != r['result'] or m is None and r['result'] >= 0:
                    reason = '   Reason: ' + r.get('reason') if 'reason' in r else ''
                    q = '"' + q + '"'
                    o += f"{q.ljust(ml)} - {rcircle} Ex: {r['result']}, Ac: {mid}{reason}\n"
                else:
                    c += 1
        if c != len(suite):
            o += f"\n\nTests complete.  {c}/{len(suite)} succeeded."
        else:
            o += "\n\n\N{LARGE GREEN CIRCLE} All tests succeeded" + random.choice('.....!!!!!?')
        for page in pagify(o):
            await ctx.send(box(page))

    @idt_name.command(name="run")
    async def idtn_run(self, ctx):
        """Run all name/fluff tests"""
        await self.norf_run(ctx)

    @idt_fluff.command(name="run")
    async def idtf_run(self, ctx):
        """Run all name/fluff tests"""
        await self.norf_run(ctx)

    async def norf_run(self, ctx):
        """Run all name/fluff tests"""
        suite = await self.config.fluff_suite()
        await self.config.user(ctx.author).lastaction.set('name')
        c = 0
        o = ""
        rcircle, ycircle = '\N{LARGE RED CIRCLE}', '\N{LARGE YELLOW CIRCLE}'
        async with ctx.typing():
            for v in suite:
                fluff = v['id'] in [m.monster_id for m in self.bot.get_cog("Dadguide").index2.fluff_tokens[v['token']]]
                name = v['id'] in [m.monster_id for m in self.bot.get_cog("Dadguide").index2.name_tokens[v['token']]]

                if (v['fluff'] and not fluff) or (not v['fluff'] and not name):
                    q = '"{}"'.format(v['token'])
                    o += f"{str(v['id']).ljust(4)} {q.ljust(10)} - " \
                         f"{ycircle if name or fluff else rcircle} " \
                         f"Not {'Fluff' if name else 'Name' if fluff else 'A'} Token\n"
                else:
                    c += 1
        if c != len(suite):
            o += f"\n\nTests complete.  {c}/{len(suite)} succeeded."
        else:
            o += "\n\n\N{LARGE GREEN CIRCLE} All tests succeeded."
        for page in pagify(o):
            await ctx.send(box(page))

    @idtest.command(name="runall")
    async def idt_runall(self, ctx):
        """Run all tests"""
        rcircle, ycircle = '\N{LARGE RED CIRCLE}', '\N{LARGE YELLOW CIRCLE}'
        dgcog = await self.get_dgcog()
        qsuite = await self.config.test_suite()
        qo = ""
        qc = 0
        ml = len(max(qsuite, key=len)) + 2
        async with ctx.typing():
            for c, q in enumerate(sorted(qsuite)):
                m = await findMonster3(dgcog, q)
                mid = m and m.monster_id
                if m is not None and m.monster_id != qsuite[q]['result'] or m is None and qsuite[q]['result'] >= 0:
                    reason = '   Reason: ' + qsuite[q].get('reason') if qsuite[q].get('reason') else ''
                    q = '"' + q + '"'
                    qo += f"{str(c).rjust(4)}. {q.ljust(ml)} - {rcircle} Ex: {qsuite[q]['result']}, Ac: {mid}{reason}\n"
                else:
                    qc += 1

        fsuite = await self.config.fluff_suite()
        fo = ""
        fc = 0
        async with ctx.typing():
            for c, v in enumerate(fsuite):
                fluff = v['id'] in [m.monster_id for m in self.bot.get_cog("Dadguide").index2.fluff_tokens[v['token']]]
                name = v['id'] in [m.monster_id for m in self.bot.get_cog("Dadguide").index2.name_tokens[v['token']]]

                if (v['fluff'] and not fluff) or (not v['fluff'] and not name):
                    q = '"{}"'.format(v['token'])
                    fo += f"{str(c).rjust(4)}. {str(v['id']).ljust(4)} {q.ljust(ml - 5)} - " \
                          f"{ycircle if name or fluff else rcircle} " \
                          f"Not {'Fluff' if name else 'Name' if fluff else 'A'} Token\n"
                else:
                    fc += 1

        o = ""
        if fo:
            o += "[Failed Token Tests]\n" + fo
        if qo:
            o += "\n[Failed Query Tests]\n" + qo

        if qc + fc != len(fsuite) + len(qsuite):
            o += f"\n\nTests complete.  {qc + fc}/{len(fsuite) + len(qsuite)} succeeded."
        else:
            o += "\n\n\N{LARGE GREEN CIRCLE} \N{LARGE GREEN CIRCLE} All tests succeeded" \
                 + random.choice(['.'] * 5 + ['!!'] * 5 + ['???'])
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

        dgcog = await self.get_dgcog()
        m, err, debug_info = await findMonsterCustom(dgcog, ctx, self.config, query)
        if m is not None:
            voice_id = m.voice_id_jp if server == 'jp' else m.voice_id_na
            if voice_id is None:
                await ctx.send(inline("No voice file found for " + m.name_en))
                return
            base_dir = settings.voiceDir()
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
            if settings.setEvoID(ctx.author.id):
                await ctx.tick()
            else:
                await ctx.send(inline("You're already using evo mode"))
        elif value in ['number']:
            if settings.rmEvoID(ctx.author.id):
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
        ess = settings.emojiServers()
        if server_id not in ess:
            ess.append(server_id)
            settings.save_settings()
        await ctx.tick()

    @emojiservers.command(name="remove", aliases=['rm', 'del'])
    @checks.is_owner()
    async def es_rm(self, ctx, server_id: int):
        """Remove the emoji server by ID"""
        ess = settings.emojiServers()
        if server_id not in ess:
            await ctx.send("That emoji server is not set.")
            return
        ess.remove(server_id)
        settings.save_settings()
        await ctx.tick()

    @emojiservers.command(name="list", aliases=['show'])
    @checks.is_owner()
    async def es_show(self, ctx):
        """List the emoji servers by ID"""
        ess = settings.emojiServers()
        await ctx.send(box("\n".join(str(s) for s in ess)))

    @padinfo.command()
    @checks.is_owner()
    async def setvoicepath(self, ctx, *, path=''):
        """Set path to the voice direcory"""
        settings.setVoiceDir(path)
        await ctx.tick()

    @checks.is_owner()
    @padinfo.command()
    async def iddiff(self, ctx):
        """Runs the diff checker for id and id3"""
        await ctx.send("Running diff checker...")
        hist_aggreg = list(historic_lookups)
        s = 0
        f = []
        dgcog = await self.get_dgcog()
        async for c, query in AsyncIter(enumerate(hist_aggreg)):
            m1, err1, debug_info1 = await findMonster1(dgcog, query)
            m2, err2, debug_info2 = await findMonster3(dgcog, query)
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
        server_ids = [int(sid) for sid in settings.emojiServers()]
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

    @commands.command(aliases=["iddebug"])
    async def debugid(self, ctx, *, query):
        """Get helpful id information about a monster"""
        dgcog = self.bot.get_cog("Dadguide")
        m = await findMonster3(dgcog, query)
        if m is None:
            await ctx.send(box("Your query didn't match any monsters."))
            return
        bm = dgcog.database.graph.get_base_monster(m)
        pfxs = dgcog.index2.modifiers[m]
        EVOANDTYPE = dgcog.token_maps.EVO_TOKENS.union(dgcog.token_maps.TYPE_TOKENS)
        o = (f"[{m.monster_id}] {m.name_en}\n"
             f"Base: [{bm.monster_id}] {bm.name_en}\n"
             f"Series: {m.series.name_en} ({m.series_id})\n\n"
             f"[Name Tokens] {' '.join(sorted(t for t, ms in dgcog.index2.name_tokens.items() if m in ms))}\n"
             f"[Fluff Tokens] {' '.join(sorted(t for t, ms in dgcog.index2.fluff_tokens.items() if m in ms))}\n\n"
             f"[Manual Tokens]\n"
             f"     Treenames: {' '.join(sorted(t for t, ms in dgcog.index2.manual_tree.items() if m in ms))}\n"
             f"     Nicknames: {' '.join(sorted(t for t, ms in dgcog.index2.manual_nick.items() if m in ms))}\n\n"
             f"[Modifier Tokens]\n"
             f"     Attribute: {' '.join(sorted(t for t in pfxs if t in dgcog.token_maps.COLOR_TOKENS))}\n"
             f"     Awakening: {' '.join(sorted(t for t in pfxs if t in dgcog.token_maps.AWAKENING_TOKENS))}\n"
             f"    Evo & Type: {' '.join(sorted(t for t in pfxs if t in EVOANDTYPE))}\n"
             f"         Other: {' '.join(sorted(t for t in pfxs if t not in dgcog.token_maps.OTHER_HIDDEN_TOKENS))}\n")
        for page in pagify(o):
            await ctx.send(box(page))

    @commands.command()
    async def debugiddist(self, ctx, s1, s2):
        dist = jaro_winkler(s1, s2)
        yes = '\N{WHITE HEAVY CHECK MARK}'
        no = '\N{CROSS MARK}'
        await ctx.send(f"Printing info for {inline(s1)}, {inline(s2)}\n" +
                       box(f"Jaro-Winkler Distance:    {round(dist, 4)}\n"
                           f"Modifier token threshold: {find_monster.MODIFIER_JW_DISTANCE}  "
                           f"{yes if dist >= find_monster.MODIFIER_JW_DISTANCE else no}\n"
                           f"Name token threshold:     {find_monster.TOKEN_JW_DISTANCE}   "
                           f"{yes if dist >= find_monster.TOKEN_JW_DISTANCE else no}"))

    @commands.command(aliases=['helpid'])
    async def idhelp(self, ctx, *, query=""):
        """Get help with an id query"""
        await ctx.send(
            "See <{0}> for documentation on `{1.prefix}id`! Use `{1.prefix}idmeaning` to query the meaning of any modifier token.".format(
                IDGUIDE, ctx))
        if query:
            await self.debugid(ctx, query=query)

    @commands.command()
    async def exportmodifiers(self, ctx):
        DGCOG = self.bot.get_cog("Dadguide")
        tms = DGCOG.token_maps
        awakenings = {a.awoken_skill_id: a for a in DGCOG.database.get_all_awoken_skills()}
        series = {s.series_id: s for s in DGCOG.database.get_all_series()}

        o = ("Jump to:\n\n"
             "* [Types](#types)\n"
             "* [Evolutions](#evolutions)\n"
             "* [Misc](#misc)\n"
             "* [Awakenings](#awakenings)\n"
             "* [Series](#series)\n"
             "* [Attributes](#attributes)\n\n\n\n")

        etable = [(k.value, ", ".join(map(inline, v))) for k, v in tms.EVO_MAP.items()]
        o += "\n\n### Evolutions\n\n" + tabulate(etable, headers=["Meaning", "Tokens"], tablefmt="github")
        ttable = [(k.name, ", ".join(map(inline, v))) for k, v in tms.TYPE_MAP.items()]
        o += "\n\n### Types\n\n" + tabulate(ttable, headers=["Meaning", "Tokens"], tablefmt="github")
        mtable = [(k.value, ", ".join(map(inline, v))) for k, v in tms.MISC_MAP.items()]
        o += "\n\n### Misc\n\n" + tabulate(mtable, headers=["Meaning", "Tokens"], tablefmt="github")
        atable = [(awakenings[k.value].name_en, ", ".join(map(inline, v))) for k, v in tms.AWOKEN_MAP.items()]
        o += "\n\n### Awakenings\n\n" + tabulate(atable, headers=["Meaning", "Tokens"], tablefmt="github")
        stable = [(series[k].name_en, ", ".join(map(inline, v)))
                  for k, v in DGCOG.index2.series_id_to_pantheon_nickname.items()]
        o += "\n\n### Series\n\n" + tabulate(stable, headers=["Meaning", "Tokens"], tablefmt="github")
        ctable = [(k.name.replace("Nil", "None"), ", ".join(map(inline, v))) for k, v in tms.COLOR_MAP.items()]
        ctable += [("Sub " + k.name.replace("Nil", "None"), ", ".join(map(inline, v))) for k, v in
                   tms.SUB_COLOR_MAP.items()]
        for k, v in tms.DUAL_COLOR_MAP.items():
            k0name = k[0].name.replace("Nil", "None")
            k1name = k[1].name.replace("Nil", "None")
            ctable.append((k0name + "/" + k1name, ", ".join(map(inline, v))))
        o += "### Attributes\n\n" + tabulate(ctable, headers=["Meaning", "Tokens"], tablefmt="github")

        await ctx.send(file=text_to_file(o, filename="table.md"))

    @commands.command(aliases=["idcheckmod", "lookupmod", "idlookupmod"])
    async def idmeaning(self, ctx, *, modifier):
        """Get all the meanings of a token (bold signifies base of a tree)"""
        modifier = modifier.replace(" ", "")
        DGCOG = self.bot.get_cog("Dadguide")

        await DGCOG.wait_until_ready()

        tms = DGCOG.token_maps
        awokengroup = "(" + "|".join(re.escape(aw) for aws in tms.AWOKEN_MAP.values() for aw in aws) + ")"
        awakenings = {a.awoken_skill_id: a for a in DGCOG.database.get_all_awoken_skills()}
        series = {s.series_id: s for s in DGCOG.database.get_all_series()}

        o = ""

        def write_name_token(dict, type, mwtoken=False):
            def f(m, s):
                return bold(s) if DGCOG.database.graph.monster_is_base(m) else s

            o = ""
            so = []
            for m in sorted(dict[modifier], key=lambda m: m.monster_id):
                if (m in DGCOG.index2.mwtoken_creators[modifier]) == mwtoken:
                    so.append(m)
            if len(so) > 5:
                o += f"\n\n{type}\n" + ", ".join(f(m, str(m.monster_id)) for m in so[:10])
                o += f"... ({len(so)} total)" if len(so) > 10 else ""
            elif so:
                o += f"\n\n{type}\n" + "\n".join(f(m, f"{str(m.monster_id).rjust(4)}. {m.name_en}") for m in so)
            return o

        o += write_name_token(DGCOG.index2.manual, "\N{LARGE PURPLE CIRCLE} [Multi-Word Tokens]", 1)
        o += write_name_token(DGCOG.index2.manual, "[Manual Tokens]")
        o += write_name_token(DGCOG.index2.name_tokens, "[Name Tokens]")
        o += write_name_token(DGCOG.index2.fluff_tokens, "[Fluff Tokens]")

        def additmods(ms, om):
            if len(ms) == 1:
                return ""
            return "\n\tAlternate names: " + ', '.join(inline(m) for m in ms if m != om)

        meanings = [
            *["Evo: " + k.value + additmods(v, modifier)
              for k, v in tms.EVO_MAP.items() if modifier in v],
            *["Type: " + get_type_emoji(k) + ' ' + k.name + additmods(v, modifier)
              for k, v in tms.TYPE_MAP.items() if modifier in v],
            *["Misc: " + k.value + additmods(v, modifier)
              for k, v in tms.MISC_MAP.items() if modifier in v],
            *["Awakening: " + get_awakening_emoji(k) + ' ' + awakenings[k.value].name_en + additmods(v, modifier)
              for k, v in tms.AWOKEN_MAP.items() if modifier in v],
            *["Main attr: " + get_attribute_emoji_by_enum(k, None) + ' ' + k.name.replace("Nil", "None") +
              additmods(v, modifier)
              for k, v in tms.COLOR_MAP.items() if modifier in v],
            *["Sub attr: " + get_attribute_emoji_by_enum(False, k) + ' ' + k.name.replace("Nil", "None") +
              additmods(v, modifier)
              for k, v in tms.SUB_COLOR_MAP.items() if modifier in v],
            *["Dual attr: " + get_attribute_emoji_by_enum(k[0], k[1]) + ' ' + k[0].name.replace("Nil", "None") +
              '/' + k[1].name.replace("Nil", "None") + additmods(v, modifier)
              for k, v in tms.DUAL_COLOR_MAP.items() if modifier in v],
            *["Series: " + series[k].name_en + additmods(v, modifier)
              for k, v in DGCOG.index2.series_id_to_pantheon_nickname.items() if modifier in v],

            *["Rarity: " + m for m in re.findall(r"^(\d+)\*$", modifier)],
            *["Base rarity: " + m for m in re.findall(r"^(\d+)\*b$", modifier)],
            *[f"[UNSUPPORTED] Multiple awakenings: {m}x {awakenings[a.value].name_en}"
              f"{additmods([f'{m}*{d}' for d in v], modifier)}"
              for m, ag in re.findall(r"^(\d+)\*{}$".format(awokengroup), modifier)
              for a, v in tms.AWOKEN_MAP.items() if ag in v]
        ]

        if meanings or o:
            for page in pagify("\n".join(meanings) + "\n\n" + o.strip()):
                await ctx.send(page)
        else:
            await ctx.send(f"There are no modifiers that match `{modifier}`.")
