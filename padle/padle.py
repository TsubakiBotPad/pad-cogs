import asyncio
import csv
import discord
import itertools
import json
import logging
import random
import re
from contextlib import suppress
from datetime import datetime
from discordmenu.embed.components import EmbedThumbnail, EmbedMain
from discordmenu.embed.view import EmbedView
from io import BytesIO, StringIO
from math import ceil
from padle.help_texts import HELP_TEXT, RULES_TEXT
from padle.menu.closable_embed import ClosableEmbedMenu
from padle.menu.globalstats import GlobalStatsMenu, GlobalStatsViewState
from padle.menu.menu_map import padle_menu_map
from padle.menu.padle_scroll import PADleScrollMenu, PADleScrollViewState
from padle.menu.personal_stats import PersonalStatsMenu
from padle.monsterdiff import MonsterDiff
from padle.view.confirmation import PADleMonsterConfirmationView, PADleMonsterConfirmationViewProps
from padle.view.personal_stats_view import PersonalStatsView, PersonalStatsViewProps
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify
from tsutils.cogs.globaladmin import auth_check
from tsutils.emoji import NO_EMOJI, YES_EMOJI
from tsutils.helper_functions import conditional_iterator
from tsutils.menu.components.config import BotConfig
from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.time import NA_TIMEZONE
from tsutils.tsubaki.custom_emoji import get_emoji
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader
from tsutils.user_interaction import get_user_confirmation, send_confirmation_message, send_cancellation_message, \
    get_user_reaction
from typing import TYPE_CHECKING, Any, List, Optional, Union

if TYPE_CHECKING:
    from dbcog.dbcog import DBCog
    # from dbcog.monster_graph import MonsterGraph # used for creating the filter

logger = logging.getLogger('red.padbot-cogs.padle')


class PADle(commands.Cog):
    """A Wordle game for PAD"""

    # Used if no monster list is set
    FALLBACK_PADLE_MONSTER = 3260
    menu_map = padle_menu_map

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=94073)
        self.config.register_user(todays_guesses=[], start=False, done=False, score=[],
                                  edit_id=0, channel_id=0, all_guesses={})
        self.config.register_global(padle_today=self.FALLBACK_PADLE_MONSTER,
                                    stored_day=self._day_today(), num_days=1, subs=[],
                                    all_scores=[], save_daily_scores=[], monsters_list=[], tmrw_padle=0)
        self.config.register_guild(allow=False)
        self._daily_padle_loop = bot.loop.create_task(self.generate_padle())
        GACOG: Any = self.bot.get_cog("GlobalAdmin")
        if GACOG:
            GACOG.register_perm("padleadmin")

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        all_guesses = await self.config.user_from_id(user_id).all_guesses()
        if all_guesses:
            data = (f"You have {len(all_guesses)} days of guess data stored. "
                    f"Here are your guesses:\n{json.dumps(all_guesses)}")
        else:
            data = f"No data is stored for user with ID {user_id}."
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data."""
        await self.config.user_from_id(user_id).clear()

    async def register_menu(self):
        await self.bot.wait_until_ready()
        menulistener: Any = self.bot.get_cog("MenuListener")
        if menulistener is None:
            logger.warning("MenuListener is not loaded.")
            return
        await menulistener.register(self)

    async def get_dbcog(self) -> "DBCog":
        dbcog: Any = self.bot.get_cog("DBCog")
        if dbcog is None:
            raise ValueError("DBCog cog is not loaded")
        await dbcog.wait_until_ready()
        return dbcog

    def cog_unload(self):
        self._daily_padle_loop.cancel()

    async def get_menu_default_data(self, ims):
        data = {
            'dbcog': await self.get_dbcog(),
            'user_config': await BotConfig.get_user(self.config, ims['original_author_id']),
            'padle_cog': self,
        }
        return data

    async def get_today_guesses(self, user: discord.User, current_day: Union[str, int]) -> Optional[List[int]]:
        if current_day is None:
            return None
        if user is None:
            return {}
        return (await self.config.user(user).all_guesses()).get(str(current_day))

    def _day_today(self):
        return datetime.now(NA_TIMEZONE).day

    @commands.group()
    async def padle(self, ctx):
        """Commands pertaining to PADle"""

    @commands.group(aliases=['padleconfig'])
    @auth_check('padleadmin')
    async def padleadmin(self, ctx):
        """Commands pertaining to PADle setup"""

    @padle.command()
    async def help(self, ctx):
        """Instructions for PADle"""
        await ctx.send(self._get_help_text(ctx))

    def _get_help_text(self, ctx):
        args = {"db": get_emoji("db"), "p": ctx.prefix, "tsubaki": get_emoji("tsubaki")}
        return HELP_TEXT.format(**args)

    @padle.command()
    async def validrules(self, ctx):
        """Show rules for the valid-answer monster list"""
        args = {"db": get_emoji("db"), "rd": get_emoji("rd")}
        await ctx.send(RULES_TEXT.format(**args))

    @padle.command(aliases=["sub"])
    async def subscribe(self, ctx, sub_arg: bool = True):
        """Subscribe to daily notifications of new PADles"""
        prefix = ctx.prefix
        subbed_users = await self.config.subs()
        if not sub_arg:
            if ctx.author.id in subbed_users:
                async with self.config.subs() as subs:
                    subs.remove(ctx.author.id)
                return await send_confirmation_message(ctx, "You will no longer receive notifications of new PADles.")
            return await send_cancellation_message(ctx, "You are not subscribed.")
        if ctx.author.id not in subbed_users:
            async with self.config.subs() as subs:
                subs.append(ctx.author.id)
            return await send_confirmation_message(ctx, "You will now receive notifications of new PADles. "
                                                        "You can unsubscribe with `{}padle subscribe 0`.".format(
                prefix))

        confirmation = await get_user_confirmation(ctx, "You are already subscribed. Did you mean to unsubscribe?")
        if confirmation:
            async with self.config.subs() as subs:
                subs.remove(ctx.author.id)
            return await send_confirmation_message(ctx, "You will no longer receive notifications of new PADles.")
        elif confirmation is None:
            await send_cancellation_message(ctx, "Confirmation timeout")
        else:
            await ctx.send("No changes were made, you will still receive notifications of new PADles.")

    async def can_play_in_guild(self, ctx):
        return (ctx.guild is not None and ctx.author.guild_permissions.administrator and ctx.guild.member_count < 10 and
                await self.config.guild(ctx.guild).allow())

    @padle.command()
    async def start(self, ctx):
        """Start a game of PADle"""
        if await self.config.user(ctx.author).done():
            return await ctx.send("You have already finished today's PADle!")
        if await self.config.user(ctx.author).start():
            return await ctx.send("You have already started a game!")
        if (ctx.guild is not None and ctx.author.guild_permissions.administrator and ctx.guild.member_count < 10 and
                not await self.config.guild(ctx.guild).allow()):
            guild_confirmation = await get_user_confirmation(ctx, "It looks like you're in a private server. "
                                                                  "Would you like to play PADle in this server"
                                                                  " rather than in DMs?", timeout=30,
                                                             force_delete=False, show_feedback=True)
            if guild_confirmation is None:
                return await send_cancellation_message(ctx, "Confirmation timeout.")
            if await self.config.guild(ctx.guild).allow():
                return await ctx.send("You have already enabled PADle in this server!")
            if not guild_confirmation:
                await send_confirmation_message(ctx, "PADles will continue being played in DMs.")
            else:
                await send_confirmation_message(ctx, "PADles can now be played in this server.")
                await self.config.guild(ctx.guild).allow.set(True)
        if ctx.guild is None:
            message = "Start today's (#{}) PADle game?".format(await self.config.num_days())
        else:
            message = "{}, start today's (#{}) PADle game?".format(ctx.author.name, await self.config.num_days())
        confirmation = await get_user_confirmation(ctx, message, timeout=30, force_delete=False, show_feedback=True)
        if confirmation is None:
            return await send_cancellation_message(ctx, "Confirmation timeout.")
        if await self.config.user(ctx.author).start():
            return await send_cancellation_message(ctx, "You cannot start multiple games!")
        if not confirmation:
            return await send_cancellation_message(ctx, "The PADle game was not started.")

        prefix = ctx.prefix
        em = discord.Embed(title="PADle #{}".format(await self.config.num_days()), type="rich",
                           description=f"Guess a card with `{prefix}padle guess <card>`!\nIf "
                                       f"you give up, use `{prefix}padle giveup`.\n"
                                       "If you accidentally deleted the guess list message,"
                                       f" use `{prefix}padle resend`.",
                           color=discord.Color.teal())
        if await self.can_play_in_guild(ctx):
            if len(await self.config.user(ctx.author).all_guesses()) == 0:
                await ctx.send("Hello! It looks like this is your first PADle game.")
                await ctx.send(self._get_help_text(ctx))
            await ctx.send(embed=em)
            await self.config.user(ctx.author).start.set(True)
            return
        # else
        try:
            if len(await self.config.user(ctx.author).all_guesses()) == 0:
                await ctx.author.send("Hello! It looks like this is your first PADle game.")
                await ctx.author.send(self._get_help_text(ctx))
            await ctx.author.send(embed=em)
        except discord.HTTPException:
            return await send_cancellation_message(ctx,
                                                   "Looks like I can't DM you. Try checking your Privacy Settings.")
        if ctx.guild is not None:
            await send_confirmation_message(ctx, f"{ctx.author.name}, check your DMs!")
        await self.config.user(ctx.author).start.set(True)

    @padle.command()
    async def globalstats(self, ctx, day: int = 0):
        """Global stats for the PADle (optionally on a specified day)"""
        num_days = await self.config.num_days()
        if day <= 0 or day > num_days:
            day = await self.config.num_days()

        if day == num_days:
            stats = await self.config.all_scores()
            monster = None
        else:
            dbcog = await self.get_dbcog()
            all = await self.config.save_daily_scores()
            stats = all[day - 1][1]
            monster = dbcog.get_monster(all[day - 1][0])
        qs = await QuerySettings.extract_raw(ctx.author, self.bot, "")
        global_stats_menu = GlobalStatsMenu.menu()
        state = GlobalStatsViewState(ctx.author.id, GlobalStatsMenu.MENU_TYPE, qs, "",
                                     current_day=day, num_days=num_days, monster=monster, stats=stats)
        await global_stats_menu.create(ctx, state)

    @padle.command()
    async def stats(self, ctx):
        """Personal PADle stats"""
        if await self.config.user(ctx.author).start() and not await self.config.user(ctx.author).done():
            return await send_cancellation_message(ctx, "Please finish today's PADle before checking your stats!")
        all_guesses = await self.config.user(ctx.author).all_guesses()
        played = len(all_guesses)
        save_daily = await self.config.save_daily_scores()
        if played == 0:
            return await send_cancellation_message(ctx, "You haven't played PADle yet!")
        cur_streak = 0
        max_streak = 0
        wins = 0
        for day in range(1, await self.config.num_days() + 1):
            if day == await self.config.num_days():
                correct_id = await self.config.padle_today()
            else:
                correct_id = save_daily[day - 1][0]
            if str(day) in all_guesses and correct_id in all_guesses[str(day)]:
                cur_streak += 1
                wins += 1
            elif day != await self.config.num_days() or await self.config.user(ctx.author).done():
                cur_streak = 0
            max_streak = max(max_streak, cur_streak)
        flatten = itertools.chain.from_iterable
        all_monsters_guessed = list(flatten(all_guesses.values()))
        if not all_monsters_guessed:
            all_monsters_guessed.append(self.FALLBACK_PADLE_MONSTER)
        mode = max(set(all_monsters_guessed), key=all_monsters_guessed.count)
        dbcog = await self.get_dbcog()
        m = dbcog.get_monster(mode)
        menu = PersonalStatsMenu.menu()
        qs = await QuerySettings.extract_raw(ctx.author, self.bot, "")
        props = PersonalStatsViewProps(qs, ctx.author.name, played, wins / played,
                                       cur_streak, max_streak, m)
        state = ClosableEmbedViewState(ctx.author.id, PersonalStatsMenu.MENU_TYPE, "", qs,
                                       PersonalStatsView.VIEW_TYPE, props)
        await menu.create(ctx, state)

    async def do_quit_early(self, ctx):
        prefix = ctx.prefix
        if ctx.guild is not None and not await self.can_play_in_guild(ctx):
            await ctx.send("You can only play PADle in DMs!")
            return True
        if not await self.config.user(ctx.author).start():
            await ctx.send(f"You have not started the game of PADle yet, try `{prefix}padle start`!")
            return True
        if await self.config.user(ctx.author).done():
            await ctx.send("You have already played today's PADle!")
            return True
        return False

    @padle.command()
    async def guess(self, ctx, *, guess):
        """Guess a card for the daily PADle"""
        if await self.do_quit_early(ctx):
            return
        dbcog = await self.get_dbcog()

        guess_monster = await dbcog.find_monster(guess, ctx.author.id)
        if guess_monster is None:
            close_menu = ClosableEmbedMenu.menu()
            props = PADleMonsterConfirmationViewProps("Monster not found, please try again.")
            qs = await QuerySettings.extract_raw(ctx.author, self.bot, guess)
            state = ClosableEmbedViewState(ctx.author.id, ClosableEmbedMenu.MENU_TYPE, guess,
                                           qs, PADleMonsterConfirmationView.VIEW_TYPE, props)
            await close_menu.create(ctx, state)
            return

        m_embed = EmbedView(
            EmbedMain(
                title=MonsterHeader.menu_title(guess_monster).to_markdown(),
                description="Did you mean this monster?"),
            embed_thumbnail=EmbedThumbnail(
                MonsterImage.icon(guess_monster.monster_id))).to_embed()
        confirmation = await get_user_reaction(ctx, m_embed, YES_EMOJI, NO_EMOJI, timeout=20)
        if confirmation is None:
            return await send_cancellation_message(ctx, "Confirmation timeout.")
        if confirmation == NO_EMOJI:
            return await send_cancellation_message(ctx, "Please guess again.")
        if not await self.config.user(ctx.author).start():
            return await send_cancellation_message(ctx,
                                                   "You have not started a game yet! The PADle may have just expired.")
        if await self.config.user(ctx.author).done():
            return await send_cancellation_message(ctx, "You have already finished today's PADle!")
        async with self.config.user(ctx.author).todays_guesses() as todays_guesses:
            todays_guesses.append(guess_monster.monster_id)
        monster = dbcog.get_monster(int(await self.config.padle_today()))
        cur_day = await self.config.num_days()
        todays_guesses = await self.config.user(ctx.author).todays_guesses()
        async with self.config.user(ctx.author).all_guesses() as all_guesses:
            all_guesses[str(cur_day)] = todays_guesses

        channel = self.bot.get_channel(await self.config.user(ctx.author).channel_id())
        if channel is not None:
            with suppress(discord.HTTPException):
                del_msg = await channel.fetch_message(await self.config.user(ctx.author).edit_id())
                await del_msg.delete()

        guess_monster_diff = MonsterDiff(monster, guess_monster)
        points = guess_monster_diff.get_diff_score()

        padle_menu = PADleScrollMenu.menu()
        # qs = await QuerySettings.extract_raw(ctx.author, self.bot, guess)
        cur_page = ceil(len(todays_guesses) / 5) - 1
        page_guesses = await PADleScrollViewState.do_queries(dbcog,
                                                             todays_guesses[((cur_page) * 5):((cur_page + 1) * 5)])
        state = PADleScrollViewState(ctx.author.id, PADleScrollMenu.MENU_TYPE, guess, monster=monster,
                                     cur_day_page_guesses=page_guesses, current_day=cur_day,
                                     current_page=cur_page, num_pages=cur_page + 1)
        message = await padle_menu.create(ctx, state)
        await self.config.user(ctx.author).edit_id.set(message.id)
        await self.config.user(ctx.author).channel_id.set(ctx.channel.id)

        score = "\N{LARGE YELLOW SQUARE}"
        if guess_monster.monster_id == monster.monster_id:
            await ctx.send("You got the PADle in {} guesses! Use `{}padle score` to share your score.".format(
                len(await self.config.user(ctx.author).todays_guesses()), ctx.prefix))
            await self.config.user(ctx.author).done.set(True)
            async with self.config.all_scores() as all_scores:
                all_scores.append(str(len(await self.config.user(ctx.author).todays_guesses())))
            score = "\N{LARGE GREEN SQUARE}"
        else:
            if points < 9:
                score = "\N{LARGE ORANGE SQUARE}"
            if points < 5:
                score = "\N{LARGE RED SQUARE}"
        async with self.config.user(ctx.author).score() as scores:
            scores.append(score)

    @padle.command()
    async def resend(self, ctx):
        """Resends the guess list message"""
        if await self.do_quit_early(ctx):
            return
        dbcog = await self.get_dbcog()
        monster = dbcog.get_monster(int(await self.config.padle_today()))
        cur_day = await self.config.num_days()
        todays_guesses = await self.config.user(ctx.author).todays_guesses()
        if len(todays_guesses) == 0:
            return await send_cancellation_message(ctx, "You haven't guessed yet!")
        padle_menu = PADleScrollMenu.menu()
        cur_page = ceil(len(todays_guesses) / 5) - 1
        page_guesses = await PADleScrollViewState.do_queries(dbcog,
                                                             todays_guesses[((cur_page) * 5):((cur_page + 1) * 5)])
        state = PADleScrollViewState(ctx.author.id, PADleScrollMenu.MENU_TYPE, monster=monster,
                                     cur_day_page_guesses=page_guesses, current_day=cur_day,
                                     current_page=cur_page, num_pages=cur_page + 1)
        message = await padle_menu.create(ctx, state)
        await self.config.user(ctx.author).edit_id.set(message.id)
        await self.config.user(ctx.author).channel_id.set(ctx.channel.id)

    @padle.command()
    async def giveup(self, ctx):
        """Give up on today's PADle"""
        if await self.do_quit_early(ctx):
            return
        confirmation = await get_user_confirmation(ctx, "Are you sure you would like to give up?", timeout=20)
        dbcog = await self.get_dbcog()
        if not confirmation:
            if confirmation is None:
                await send_cancellation_message(ctx, "Confirmation timeout.")
            return
        monster = dbcog.get_monster(int(await self.config.padle_today()))
        await self.config.user(ctx.author).done.set(True)
        m_embed = EmbedView(EmbedMain(title=MonsterHeader.menu_title(monster).to_markdown(),
                                      description="PADle #{}".format(await self.config.num_days()),
                                      url=MonsterLink.ilmina(monster), color=discord.Color.red()),
                            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(monster.monster_id))).to_embed()
        await ctx.send(embed=m_embed)
        await ctx.send(f"Use `{ctx.prefix}padle score` to share your score!")
        async with self.config.user(ctx.author).score() as scores:
            scores.append("\N{CROSS MARK}")
        async with self.config.all_scores() as all_scores:
            all_scores.append("X")
        cur_day = await self.config.num_days()
        todays_guesses = await self.config.user(ctx.author).todays_guesses()
        async with self.config.user(ctx.author).all_guesses() as all_guesses:
            all_guesses[str(cur_day)] = todays_guesses

    @padle.command(aliases=["share"])
    async def score(self, ctx):
        """Share your PADle score"""
        prefix = ctx.prefix
        if not await self.config.user(ctx.author).done():
            await ctx.send("You have not done today's PADle yet!")
            return
        score = await self.config.user(ctx.author).score()
        value = "X" if "\N{CROSS MARK}" in score else str(len(await self.config.user(ctx.author).todays_guesses()))
        if ctx.guild is None:
            msg = "PADle #{}: {}".format(await self.config.num_days(), value) + "\n" + "".join(score)
            await ctx.send(msg)
            await ctx.send(f"*Hint: You can use the command `{prefix}padle score` anywhere "
                           f"and have {ctx.me.name} automatically share your score for you!*")
        else:
            await ctx.message.delete()
            msg = ctx.author.mention + "'s PADle #{}: {}".format(await self.config.num_days(), value) + "\n" + "".join(
                score)
            await ctx.send(msg)

    async def generate_padle(self):
        async def is_day_change():
            cur_day = self._day_today()
            old_day = await self.config.stored_day()
            if cur_day != old_day:
                await self.config.stored_day.set(cur_day)
                return True

        await self.bot.wait_until_ready()
        async for _ in conditional_iterator(is_day_change, poll_interval=10):
            try:
                async with self.config.save_daily_scores() as save_daily:
                    save_daily.append([await self.config.padle_today(), await self.config.all_scores()])
                tmrw_padle = await self.config.tmrw_padle()
                if tmrw_padle == 0:
                    MONSTERS_LIST = await self.config.monsters_list()
                    if len(MONSTERS_LIST) == 0:
                        await self.config.padle_today.set(self.FALLBACK_PADLE_MONSTER)
                    else:
                        await self.config.padle_today.set(int(random.choice(MONSTERS_LIST)))
                else:
                    await self.config.padle_today.set(tmrw_padle)
                    await self.config.tmrw_padle.set(0)
                num = await self.config.num_days()
                await self.config.num_days.set(num + 1)
                all_users = await self.config.all_users()
                await self.config.all_scores.set([])
                for userid in all_users:
                    user = self.bot.get_user(userid)
                    if user is None:
                        continue
                    # save past guesses only if started
                    if await self.config.user(user).start():
                        async with self.config.user(user).all_guesses() as all_guesses:
                            all_guesses[str(num)] = await self.config.user(user).todays_guesses()
                    await self.config.user(user).todays_guesses.set([])
                    # need to send message if a user is mid-game
                    if await self.config.user(user).start() and not await self.config.user(user).done():
                        await user.send("The PADle expired; a new one is available.")
                    await self.config.user(user).start.set(False)
                    await self.config.user(user).done.set(False)
                    await self.config.user(user).score.set([])
                    await self.config.user(user).edit_id.set(0)
                    await self.config.user(user).channel_id.set(0)
                subbed_users = await self.config.subs()
                for userid in subbed_users:
                    user = self.bot.get_user(userid)
                    if user is not None:
                        await user.send("PADle #{} is now available!".format(await self.config.num_days()))
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error in loop:")

    @padleadmin.command()
    async def fullreset(self, ctx):
        """Resets all stats and information"""
        confirmation = await get_user_confirmation(ctx,
                                                   "Fully reset all stats and data in PADle? You cannot undo this!")
        if confirmation is None:
            return await send_cancellation_message(ctx, "Confirmation timeout.")
        if not confirmation:
            return await send_cancellation_message(ctx, "Nothing was reset.")

        MONSTERS_LIST = await self.config.monsters_list()
        if len(MONSTERS_LIST) == 0:
            await self.config.padle_today.set(self.FALLBACK_PADLE_MONSTER)
        else:
            await self.config.padle_today.set(int(random.choice(MONSTERS_LIST)))
        await self.config.stored_day.set(self._day_today())
        await self.config.tmrw_padle.set(0)
        await self.config.num_days.set(1)
        await self.config.subs.set([])
        await self.config.all_scores.set([])
        await self.config.save_daily_scores.set([])
        all_users = await self.config.all_users()
        for userid in all_users:
            user = self.bot.get_user(userid)
            if user is None:
                continue
            await self.config.user(user).todays_guesses.set([])
            # need to send message if a user is mid-game
            if await self.config.user(user).start() and not await self.config.user(user).done():
                try:
                    await user.send("A full reset occured, the PADle expired.")
                except:
                    pass
            await self.config.user(user).start.set(False)
            await self.config.user(user).done.set(False)
            await self.config.user(user).score.set([])
            await self.config.user(user).edit_id.set(0)
            await self.config.user(user).channel_id.set(0)
            await self.config.user(user).all_guesses.set({})
        await ctx.tick()

    @padleadmin.command()
    async def add(self, ctx, *ids: int):
        """Adds space-separated list of monster IDs to the list of possible PADles"""
        dbcog = await self.get_dbcog()
        result = []
        valids = []
        monsters_list = await self.config.monsters_list()
        for monster_id in ids:
            m = dbcog.get_monster(monster_id)
            if m is None:
                result.append(f"{monster_id} is not a valid monster ID.")
                continue
            if not m.on_na or m.name_en is None:
                result.append(f"{monster_id} is not a monster on the NA server.")
                continue
            if monster_id in monsters_list:
                result.append(
                    f"{MonsterHeader.menu_title(m, use_emoji=True).to_markdown()} is already a possible PADle.")
                continue
            valids.append(monster_id)
            result.append(f"{MonsterHeader.menu_title(m, use_emoji=True).to_markdown()} was added.")
        async with self.config.monsters_list() as m_list:
            m_list.extend(valids)
        for page in pagify("\n".join(result)):
            await ctx.send(page)

    @padleadmin.command()
    async def remove(self, ctx, *ids: int):
        """Removes space-separated list of monster IDs to the list of possible PADles"""
        dbcog = await self.get_dbcog()
        result = []
        valids = []
        monsters_list = await self.config.monsters_list()
        for id in ids:
            m = dbcog.get_monster(id)
            if m is None:
                result.append(f"{str(id)} is not a valid monster ID.")
                continue
            if not m.on_na or m.name_en is None:
                result.append(f"{str(id)} is not a monster on the NA server.")
                continue
            if int(id) not in monsters_list:
                result.append(f"{MonsterHeader.menu_title(m, use_emoji=True).to_markdown()} is not a possible PADle.")
                continue
            valids.append(int(id))
            result.append(f"{MonsterHeader.menu_title(m, use_emoji=True).to_markdown()} was removed.")
        await self.config.monsters_list.set([m for m in monsters_list if m not in valids])
        for page in pagify("\n".join(result)):
            await ctx.send(page)

    @padleadmin.command()
    async def set(self, ctx):
        """Set possible PADles to attached CSV/text file"""
        if ctx.message.attachments:
            try:
                input = StringIO((await ctx.message.attachments[0].read()).decode("utf-8"))
                reader = csv.reader(input, delimiter=",")
                valid = []
                invalid = []
                dbcog = await self.get_dbcog()
                for row in reader:
                    for text_id in row:
                        id = re.sub(" ", "", text_id)
                        if not id.isnumeric():
                            invalid.append(id)
                            continue
                        m = dbcog.get_monster(int(id))
                        if m is None or not m.on_na or m.name_en is None:
                            invalid.append(id)
                            continue
                        valid.append(int(id))
                if len(invalid) == 0:
                    await self.config.monsters_list.set(valid)
                    return await ctx.tick()
                await send_cancellation_message(ctx, "The following IDs were invalid: "
                                                     f"{', '.join(invalid)}. Please remove them and try again.")
            except Exception as e:
                await send_cancellation_message(ctx, "Something went wrong.")
                logger.exception("Error when setting CSV of PADles.")
        else:
            return await send_cancellation_message(ctx, "Looks like no file was attached!")

    @padleadmin.command()
    async def list(self, ctx):
        """Lists all possible PADles"""
        dbcog = await self.get_dbcog()
        monsters_list = await self.config.monsters_list()
        monsters_list.sort()
        result = []
        for id in monsters_list:
            m = dbcog.get_monster(int(id))
            if m is None or not m.on_na or m.name_en is None:
                # this should never happen but just in case
                result.append(f"**Error**: {id} is a valid PADle but not a monster.")
                continue
            result.append(MonsterHeader.menu_title(m, use_emoji=True).to_markdown())
        for page in pagify("\n".join(result)):
            await ctx.send(page)
        await ctx.send(f"There are **{len(result)}** valid PADles!")

    @padleadmin.command(aliases=["settmrw", "settmrwpadle"])
    async def settomorrowpadle(self, ctx, id: int):
        """Sets tomorrow's PADle to a specified monster ID"""
        dbcog = await self.get_dbcog()
        monsters_list = await self.config.monsters_list()
        if id == 0:
            confirmation = await get_user_confirmation(ctx, "Would you like to make tomorrow's PADle random?")
            if confirmation is None:
                return await send_cancellation_message(ctx, "Confirmation timeout")
            if not confirmation:
                return await ctx.send("No changes were made.")
            await self.config.tmrw_padle.set(0)
            return await send_confirmation_message(ctx, "Tomorrow's PADle will be random.")
        if id not in monsters_list:
            # for the most part, avoid abuse and ensure validness
            return await ctx.send("This monster is not a valid PADle. If you would like to set it as tomorrow's"
                                  " PADle, please add it to the list of PADles first.")
        m = dbcog.get_monster(id)
        title = MonsterHeader.menu_title(m, use_emoji=True).to_markdown()
        confirmation = await get_user_confirmation(ctx, "Are you sure you would like to change tomorrow's PADle to "
                                                        f"{title}?")
        if confirmation is None:
            return await send_cancellation_message(ctx, "Confirmation timeout")
        if not confirmation:
            return await ctx.send("No change to tomorrow's PADle was made.")
        await self.config.tmrw_padle.set(id)
        prefix = ctx.prefix
        await send_confirmation_message(ctx, f"Tomorrow's PADle will be {title}! "
                                             f"Use `{prefix}padle settomorrowpadle 0` to undo this.")

    @padleadmin.command(aliases=["isin"])
    async def contains(self, ctx, *, query):
        """Checks if a monster is in the list of possible PADles"""
        monsters_list = await self.config.monsters_list()
        dbcog = await self.get_dbcog()
        monster = await dbcog.find_monster(query, ctx.author.id)
        if monster is None:
            return
        title = MonsterHeader.menu_title(monster, use_emoji=True).to_markdown()
        if monster.monster_id in monsters_list:
            return await send_confirmation_message(ctx, f"{title} is a possible PADle.")
        await send_cancellation_message(ctx, f"{title} is not a possible PADle.")

    @padleadmin.command()
    async def advance(self, ctx):
        """Advance day"""
        confirmation = await get_user_confirmation(ctx, "Advance to the next day? You cannot undo this!")
        if confirmation is None:
            return await send_cancellation_message(ctx, "Confirmation timeout.")
        if not confirmation:
            return await send_cancellation_message(ctx, "The PADle was unchanged.")
        try:
            await self.config.stored_day.set(self._day_today())
            async with self.config.save_daily_scores() as save_daily:
                save_daily.append([await self.config.padle_today(), await self.config.all_scores()])
            tmrw_padle = await self.config.tmrw_padle()
            if tmrw_padle == 0:
                MONSTERS_LIST = await self.config.monsters_list()
                if len(MONSTERS_LIST) == 0:
                    await self.config.padle_today.set(self.FALLBACK_PADLE_MONSTER)
                else:
                    await self.config.padle_today.set(int(random.choice(MONSTERS_LIST)))
            else:
                await self.config.padle_today.set(tmrw_padle)
                await self.config.tmrw_padle.set(0)
            num = await self.config.num_days()
            await self.config.num_days.set(num + 1)
            all_users = await self.config.all_users()
            await self.config.all_scores.set([])
            for userid in all_users:
                user = self.bot.get_user(userid)
                if user is None:
                    continue
                # save past guesses only if started
                if await self.config.user(user).start():
                    async with self.config.user(user).all_guesses() as all_guesses:
                        all_guesses[str(num)] = await self.config.user(user).todays_guesses()
                await self.config.user(user).todays_guesses.set([])
                # need to send message if a user is mid-game
                if await self.config.user(user).start() and not await self.config.user(user).done():
                    await user.send("The PADle expired; a new one is available.")
                await self.config.user(user).start.set(False)
                await self.config.user(user).done.set(False)
                await self.config.user(user).score.set([])
                await self.config.user(user).edit_id.set(0)
                await self.config.user(user).channel_id.set(0)
            subbed_users = await self.config.subs()
            for userid in subbed_users:
                user = self.bot.get_user(userid)
                if user is not None:
                    await user.send("PADle #{} is now available!".format(await self.config.num_days()))
            await ctx.tick()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error in loop:")

    @padleadmin.command()
    async def filter(self, ctx):
        """Re-creates the list of monsters"""
        dbcog = await self.get_dbcog()
        graph = dbcog.database.graph
        final = []
        for i in range(1, graph.max_monster_id + 1):
            monster = dbcog.get_monster(i)
            if monster is None:
                continue
            if self.is_valid_padle(monster, graph):
                final.append(str(i))
        await ctx.send("List of monsters:", file=discord.File(BytesIO(",".join(final).encode('utf-8')), "result.txt"))
        await ctx.tick()

    def is_valid_padle(self, monster, graph):
        next_trans = graph.get_next_transform(monster)
        prev_trans = graph.get_prev_transform(monster)
        return (  # Monster is in NA
                monster.name_en is not None and monster.on_na and
                # No collab monsters
                monster.series.series_type != 'collab' and
                # No equips
                not monster.is_equip and
                # No monsters with next transforms
                next_trans is None and
                monster.level >= 99 and
                # A GFE (max transformed or has SA)
                ((monster.sell_mp >= 50000 and (monster.superawakening_count > 1 or prev_trans is not None)) or
                 # OR a Super Reincarnated evo of a pantheon
                 ("Super Reincarnated" in monster.name_en and monster.sell_mp == 5000) or
                 # OR 15k non-collab, non-event monsters with SA / max transformed
                 (monster.sell_mp == 15000 and (monster.superawakening_count > 1 or prev_trans is not None) and
                  monster.series.series_type == 'regular'))
        )
