import discord
import datetime
import random
import asyncio
import logging

from typing import TYPE_CHECKING
from aiofiles import open as aopen
from typing import List, Literal, Optional
from redbot.core import Config, commands
from math import ceil

if TYPE_CHECKING:
    from dbcog.dbcog import DBCog
    # from dbcog.monster_graph import MonsterGraph # used for creating the filter
    
from tsutils.tsubaki.custom_emoji import get_awakening_emoji, get_rarity_emoji, get_type_emoji, get_emoji
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from tsutils.cogs.userpreferences import get_user_preference
from tsutils.helper_functions import conditional_iterator
from tsutils.user_interaction import get_user_confirmation, send_confirmation_message, send_cancellation_message
from tsutils.emoji import NO_EMOJI, SendableEmoji, YES_EMOJI

from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.query_settings.query_settings import QuerySettings
from padle.closable_embed import ClosableEmbedMenu
from padle.confirmation import PADleMonsterConfirmationView, PADleMonsterConfirmationViewProps
from padle.menu_map import padle_menu_map

from discordmenu.embed.components import EmbedThumbnail, EmbedMain
from discordmenu.embed.view import EmbedView
from redbot.core.utils import menus
from redbot.core.utils.menus import (
    next_page,
    prev_page,
    start_adding_reactions
)

logger = logging.getLogger('red.padbot-cogs.padle')

class PADle(commands.Cog):
    """PADle"""

    menu_map = padle_menu_map
    
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=630817360)
        self.config.register_user(guesses=[], start=False, done=False, score=[],
                                  edit_id="", channel_id="", embed_text=[])
        self.config.register_global(padle_today=3260, stored_day=0, num_days=0,
                                    subs=[], all_scores=[], save_daily_scores=[])

        self._daily_padle_loop = bot.loop.create_task(self.generate_padle())
        
    async def register_menu(self):
        await self.bot.wait_until_ready()
        menulistener = self.bot.get_cog("MenuListener")
        if menulistener is None:
            logger.warning("MenuListener is not loaded.")
            return
        await menulistener.register(self)

    async def get_menu_default_data(self, ims):
        data = {}
        return data
    
    async def get_dbcog(self) -> "DBCog":
        dbcog = self.bot.get_cog("DBCog")
        if dbcog is None:
            raise ValueError("DBCog cog is not loaded")
        await dbcog.wait_until_ready()
        return dbcog

    @commands.group()
    async def padle(self, ctx):
        """Commands pertaining to PADle"""

    @padle.command()
    async def help(self, ctx):
        """Instructions for PADle"""
        prefix=ctx.prefix
        await ctx.send("- PADle is similar to Wordle, except for PAD cards.\n"
                       "- You have infinite tries to guess the hidden PAD card (chosen from a list "
                       "of more well-known monsters). Everyone is trying to guess the same PAD card. "
                       "With each guess, you are given feedback as to how similar the two cards are, "
                       "including comparing the awakenings, rarity, typings, attributes, and monster "
                       "point sell value.\n- A new PADle is available every day. "
                       "Use `{}padle start` to begin!".format(prefix))

    @padle.command(aliases=["sub"])
    async def subscribe(self, ctx, sub_arg:bool=True):
        """Subscribe to daily notifications of new PADles"""
        prefix=ctx.prefix
        subbed_users = await self.config.subs()
        if not sub_arg:
            if ctx.author.id in subbed_users:
                return await self.unsubscribe(ctx)
            return await send_cancellation_message(ctx, "You are not subscribed.")
        if ctx.author.id not in subbed_users:
            async with self.config.subs() as subs:
                subs.append(ctx.author.id)
            return await send_confirmation_message(ctx, "You will now recieve notifications of new PADles. "
                                                   "You can unsubscribe with `{}padle subscribe 0`.".format(prefix))

        confirmation = await get_user_confirmation(ctx, "You are already subscribed. Did you mean to unsubscribe?")
        if confirmation:
            await self.unsubscribe(ctx)
        elif confirmation is None:
            await send_cancellation_message(ctx, "Confirmation timeout")
        else:
            await ctx.send("No changes were made, you will still recieve notifications of new PADles.")

    async def unsubscribe(self, ctx):
        async with self.config.subs() as subs:
            subs.remove(ctx.author.id)
        return await send_confirmation_message(ctx, "You will no longer recieve notifications of new PADles.")

    @padle.command()
    async def start(self, ctx):
        """Start a game of PADle"""
        if await self.config.user(ctx.author).done():
            return await ctx.send("You have already finished today's PADle!")
        if await self.config.user(ctx.author).start():
            return await ctx.send("You have already started a game!")
        confirmation = await get_user_confirmation(ctx, "Start today's (#{}) PADle game?".format(
            await self.config.num_days()), timeout=30, force_delete=False, show_feedback=True)
        if confirmation is None:
            return await send_cancellation_message(ctx, "Confirmation timeout.")
        if await self.config.user(ctx.author).start():
            return await send_cancellation_message(ctx, "You cannot start multiple games!")
        if not confirmation:
            return

        prefix=ctx.prefix
        em = discord.Embed(title="PADle #{}".format(await self.config.num_days()), type="rich",
                           description="Guess a card with `{}padle guess <card>`!\nIf "
                           "you give up, use `{}padle giveup`.".format(prefix,prefix))
        try:
            message = await ctx.author.send(embed=em)
        except discord.Forbidden:
            return await send_cancellation_message(ctx, "Looks like I can't DM you. Try checking your Privacy Settings.")
        if ctx.guild is not None:
            await send_confirmation_message(ctx, "Check your DMs!")
        await self.config.user(ctx.author).start.set(True)
        await self.config.user(ctx.author).edit_id.set(message.id)
        await self.config.user(ctx.author).channel_id.set(message.channel.id)
        await self.config.user(ctx.author).embed_text.set([])

    @padle.command(aliases=["stats"])
    async def globalstats(self, ctx, day: int = 0):
        """Gives global stats for the PADle (optionally on a specified day)"""
        num_days = await self.config.num_days()
        if day <= 0 or day > num_days:
            day = await self.config.num_days()
        if day == num_days:
            stats = await self.config.all_scores()
            giveups = 0
            completes = 0
            average = 0
            for item in stats:
                if item == "X":
                    giveups += 1
                else:
                    completes += 1
                    average += int(item)
            embed = discord.Embed(title="PADle #{} Stats".format(await self.config.num_days()), type="rich")
            if completes == 0:
                embed.description = ("**Total Wins**: {}\n**Total Losses**: {}\n**Win Rate**: 0%\n"
                                    "**Average Guess Count**: 0").format(completes, giveups)
            else:
                embed.description = ("**Total Wins**: {}\n**Total Losses**: {}\n**Win Rate**: {:.2%}\n"
                                    "**Average Guess Count**: {:.2f}").format(completes, giveups,
                                                                            completes / (completes + giveups),
                                                                            (average / completes))
        else:
            embed = await self.get_past_padle_embed(ctx, day)
        await ctx.send(embed=embed)
        
    async def get_past_padle_embed(self, ctx, day):
        dbcog = await self.get_dbcog()
        daily_scores = await self.config.save_daily_scores()
        info = daily_scores[day-1]
        stats = info[1]
        giveups = 0
        completes = 0
        average = 0
        for item in stats:
            if item == "X":
                giveups += 1
            else:
                completes += 1
                average += int(item)
        guess_monster = dbcog.get_monster(int(info[0]))
        embed = EmbedView(
            EmbedMain(
                title="PADle #{} Stats".format(day)),
                embed_thumbnail=EmbedThumbnail(
                    MonsterImage.icon(guess_monster.monster_id))).to_embed()
        if completes == 0:
            embed.description = ("**"+MonsterHeader.menu_title(guess_monster).to_markdown()+"**\n" +
                                 "**Total Wins**: {}\n**Total Losses**: {}\n**Win Rate**: 0%\n"
                                    "**Average Guess Count**: 0").format(completes, giveups)
        else:
            embed.description = ("**"+MonsterHeader.menu_title(guess_monster).to_markdown()+"**" +
                                "**Total Wins**: {}\n**Total Losses**: {}\n**Win Rate**: {:.2%}\n"
                                "**Average Guess Count**: {:.2f}").format(completes, giveups, 
                                                                          completes / (completes + giveups), 
                                                                          (average / completes))
        return embed
    
    @padle.command()
    @commands.is_owner()
    async def fullreset(self, ctx):
        """Resets all stats and information."""
        with open("./pad-cogs/padle/monsters.txt", "r") as f:
            monsters = f.readline().split(",")
            await self.config.padle_today.set(random.choice(monsters))

        await self.config.num_days.set(1)
        await self.config.subs.set([])
        await self.config.all_scores.set([])
        await self.config.save_daily_scores.set([])
        all_users = await self.config.all_users()
        for userid in all_users:
            user = self.bot.get_user(userid)
            if user is None:
                continue
            await self.config.user(user).guesses.set([])
            # need to send message if a user is mid-game
            if await self.config.user(user).start() and not await self.config.user(user).done():
                try:
                    await user.send("A full reset occured, the PADle expired.")
                except:
                    pass
            await self.config.user(user).start.set(False)
            await self.config.user(user).done.set(False)
            await self.config.user(user).score.set([])
            await self.config.user(user).edit_id.set("")
            await self.config.user(user).channel_id.set("")
            await self.config.user(user).embed_text.set([])
        await ctx.tick()

    # this takes a long time to run
    # @padle.command()
    # async def filter(self, ctx):
    #     dbcog = await self.get_dbcog()
    #     mgraph = dbcog.database.graph
    #     final = []
    #     for i in range(0, graph.max_monster_id):
    #         monster = await dbcog.find_monster(str(i), ctx.author)
    #         try:
    #             nextTrans = mgraph.get_next_transform(monster)
    #             prevTrans = mgraph.get_prev_transform(monster)
    #             if(monster is not None and monster.name_en is not None and monster.on_na and
    #                 ((monster.sell_mp >= 50000 and (monster.superawakening_count > 1 or prevTrans is not None)) or
    #                  "Super Reincarnated" in monster.name_en) and not monster.is_equip and
    #                     nextTrans is None and monster.level >= 99):
    #                 final.append(str(i))
    #         except Exception as e:
    #             print("Error " + str(i))
    #             pass
    #     await ctx.tick()
    #     print(",".join(final))

    @padle.command()
    async def guess(self, ctx, *, guess):
        """Guess a card for the daily PADle"""
        prefix=ctx.prefix
        if ctx.guild is not None:
            return await ctx.send("You can only play PADle in DMs!")
        if not await self.config.user(ctx.author).start():
            return await ctx.send("You have not started the game of PADle yet, try `{}padle start`!".format(prefix))
        if await self.config.user(ctx.author).done():
            return await ctx.send("You have already played today's PADle!")
        dbcog = await self.get_dbcog()

        guess_monster = await dbcog.find_monster(guess, ctx.author.id)
        if guess_monster is None:
            close_menu = ClosableEmbedMenu.menu()
            props = PADleMonsterConfirmationViewProps("Monster not found, please try again.")
            query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, guess)
            state = ClosableEmbedViewState(ctx.author.id, ClosableEmbedMenu.MENU_TYPE, guess,
                                           query_settings, PADleMonsterConfirmationView.VIEW_TYPE, props)
            await close_menu.create(ctx, state)
            return

        m_embed = EmbedView(
            EmbedMain(
                title=MonsterHeader.menu_title(guess_monster).to_markdown(),
                description="Did you mean this monster?"),
            embed_thumbnail=EmbedThumbnail(
                MonsterImage.icon(guess_monster.monster_id))).to_embed()
        confirmation = await self.get_embed_user_conf(ctx, m_embed, timeout=20)
        if confirmation is None:
            return await send_cancellation_message(ctx, "Confirmation timeout.")
        if confirmation is False:
            return await send_cancellation_message(ctx, "Please guess again.")
        if not await self.config.user(ctx.author).start():
            return await send_cancellation_message(ctx, "You have not started a game yet! The PADle may have just expired.")
        if await self.config.user(ctx.author).done():
            return await send_cancellation_message(ctx, "You have already finished today's PADle!")
            
        points = 0
        async with self.config.user(ctx.author).guesses() as guesses:
            guesses.append(guess_monster.monster_id)
        monster = dbcog.get_monster(int(await self.config.padle_today()))
        line = await self.get_name_line(ctx, monster, guess_monster)
        other_line = await self.get_other_info_line(ctx, monster, guess_monster)
        awakenings_line = await self.get_awakenings_line(ctx, monster, guess_monster)
        data = [line[0], other_line[0], awakenings_line[0]]
        points += line[1] + other_line[1] + awakenings_line[1]

        async with self.config.user(ctx.author).embed_text() as descr:
            descr.append("\n".join(data))
        embed_texts = await self.config.user(ctx.author).embed_text()
        channel = self.bot.get_channel(await self.config.user(ctx.author).channel_id())
        del_msg = await channel.fetch_message(await self.config.user(ctx.author).edit_id())
        await del_msg.delete()
        embed_pages = []
        embed_controls = {
            "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}": prev_page,
            "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}": next_page,
        }
        emojis = ["\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
                  "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}"]
        num_pages = ceil(len(embed_texts) / 5)
        for pageNum in range(ceil(len(embed_texts) / 5)):
            embed = discord.Embed(title="Padle #{}".format(await self.config.num_days()), type="rich")
            for index, text in enumerate(embed_texts[:5]):
                embed.add_field(name="**Guess {}**:".format(index + 1 + pageNum * 5), value=text, inline=False)
            embed.set_footer(text="Page {}/{}".format((pageNum + 1), num_pages))
            embed_texts = embed_texts[5:]
            embed_pages.append(embed)
        message = await ctx.send(embed=discord.Embed(title="Padle"))
        await self.config.user(ctx.author).edit_id.set(message.id)
        await self.config.user(ctx.author).channel_id.set(ctx.channel.id)
        score = "\N{LARGE YELLOW SQUARE}"
        if guess_monster.monster_id == monster.monster_id:
            await ctx.send("You got the PADle in {} guesses! Use `{}padle score` to share your score.".format(
                len(await self.config.user(ctx.author).guesses()), prefix))
            await self.config.user(ctx.author).done.set(True)
            async with self.config.all_scores() as all_scores:
                all_scores.append(str(len(await self.config.user(ctx.author).guesses())))
            score = "\N{LARGE GREEN SQUARE}"
        else:
            if points < 9:
                score = "\N{LARGE ORANGE SQUARE}"
            if points < 5:
                score = "\N{LARGE RED SQUARE}"
        async with self.config.user(ctx.author).score() as scores:
            scores.append(score)
        start_adding_reactions(message, emojis)
        await menus.menu(ctx, embed_pages, embed_controls, message=message, page=len(embed_pages) - 1, timeout=60 * 60)

    @padle.command()
    async def giveup(self, ctx):
        """Give up on today's PADle"""
        prefix = ctx.prefix
        if ctx.guild is not None:
            return await ctx.send("You can only play PADle in DMs!")
        if not await self.config.user(ctx.author).start():
            return await ctx.send("You have not started the game of PADle yet, try `{}padle start`!".format(prefix))
        if await self.config.user(ctx.author).done():
            return await ctx.send("You have already played today's PADle!")
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
                                      url=MonsterLink.ilmina(monster)),
                            embed_thumbnail=EmbedThumbnail(MonsterImage.icon(monster.monster_id))).to_embed()
        await ctx.send(embed=m_embed)
        await ctx.send("Use `{}padle score` to share your score!".format(prefix))
        async with self.config.user(ctx.author).score() as scores:
            scores.append("\N{CROSS MARK}")
        async with self.config.all_scores() as all_scores:
            all_scores.append("X")

    @padle.command()
    async def score(self, ctx):
        """Share your PADle score"""
        prefix=ctx.prefix
        if not await self.config.user(ctx.author).done():
            await ctx.send("You have not done today's PADle yet!")
            return
        score = await self.config.user(ctx.author).score()
        value = "X" if "\N{CROSS MARK}" in score else len(await self.config.user(ctx.author).guesses())
        if ctx.guild is None:
            msg = "PADle #{}: {}".format(await self.config.num_days(), value) + "\n" + "".join(score)
            await ctx.send(msg)
            await ctx.send("*Hint: You can use the command `{}padle score` anywhere "
                            "and have Tsubaki automatically share your score for you!*".format(prefix))
        else:
            await ctx.message.delete()
            msg = ctx.author.mention + "'s PADle #{}: {}".format(await self.config.num_days(), value) +"\n" + "".join(score)
            await ctx.send(msg)
            

    async def generate_padle(self):
        async def is_day_change():
            cur_day = datetime.datetime.now().day
            old_day = await self.config.stored_day()
            if cur_day != old_day:
                await self.config.stored_day.set(cur_day)
                return True

        await self.bot.wait_until_ready()
        async for _ in conditional_iterator(is_day_change, poll_interval=10):
            try:
                async with self.config.save_daily_scores() as save_daily:
                    save_daily.append([await self.config.padle_today(), await self.config.all_scores()])
                async with aopen("./pad-cogs/padle/monsters.txt", "r") as f:
                    monsters = (await f.readline()).split(",")
                    await self.config.padle_today.set(random.choice(monsters))
                num = await self.config.num_days()
                await self.config.num_days.set(num + 1)
                all_users = await self.config.all_users()
                await self.config.all_scores.set([])
                for userid in all_users:
                    user = self.bot.get_user(userid)
                    if user is None:
                        continue
                    await self.config.user(user).guesses.set([])
                    # need to send message if a user is mid-game
                    if await self.config.user(user).start() and not await self.config.user(user).done():
                        await user.send("The PADle expired; a new one is available.")
                    await self.config.user(user).start.set(False)
                    await self.config.user(user).done.set(False)
                    await self.config.user(user).score.set([])
                    await self.config.user(user).edit_id.set("")
                    await self.config.user(user).channel_id.set("")
                    await self.config.user(user).embed_text.set([])
                subbed_users = await self.config.subs()
                for userid in subbed_users:
                    user = self.bot.get_user(userid)
                    if user is not None:
                        await user.send("PADle #{} is now available!".format(await self.config.num_days()))
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error in loop:")

    async def get_name_line(self, ctx, monster, guess_monster):
        line = []
        attr1 = guess_monster.attr1.name.lower()
        attr2 = guess_monster.attr2.name.lower()
        attr_feedback = []
        attr_feedback.append("\N{WHITE HEAVY CHECK MARK}" if attr1 == monster.attr1.name.lower() else "\N{CROSS MARK}")
        attr_feedback.append("\N{WHITE HEAVY CHECK MARK}" if attr2 == monster.attr2.name.lower() else "\N{CROSS MARK}")
        if (attr1 == monster.attr2.name.lower() and
            attr2 != monster.attr2.name.lower() and attr1 != monster.attr1.name.lower()):
            attr_feedback[0] = "\N{LARGE YELLOW SQUARE}"
        if (attr2 == monster.attr1.name.lower() and
            attr2 != monster.attr2.name.lower() and attr1 != monster.attr1.name.lower()):
            attr_feedback[1] = "\N{LARGE YELLOW SQUARE}"
        line.append(get_emoji("orb_{}".format(attr1)))
        line.append(attr_feedback[0] + " / ")
        line.append(get_emoji("orb_{}".format(attr2)))
        line.append(attr_feedback[1] + " ")
        line.append("[" + str(guess_monster.monster_id) + "] ")
        line.append(guess_monster.name_en)
        points = (1 if attr1 == monster.attr1.name.lower() else 0) + (1 if attr2 == monster.attr2.name.lower() else 0)
        return ["".join(line), points]

    async def get_awakenings_line(self, ctx, monster, guess_monster):
        awakes = []
        unused = []
        feedback = []
        points = 0
        for index, guess_awakening in enumerate(guess_monster.awakenings[:9]):
            awakes.append(get_awakening_emoji(guess_awakening.awoken_skill_id, guess_awakening.name))
            if (index < len(monster.awakenings) and
               monster.awakenings[index].awoken_skill_id == guess_awakening.awoken_skill_id):
                feedback.append("\N{WHITE HEAVY CHECK MARK}")
                points += 1
            else:
                feedback.append("\N{CROSS MARK}")
                if index < len(monster.awakenings):
                    unused.append(monster.awakenings[index].awoken_skill_id)
        for index, guess_awakening in enumerate(guess_monster.awakenings[:9]):
            if guess_awakening.awoken_skill_id in unused and feedback[index] != "\N{WHITE HEAVY CHECK MARK}":
                feedback[index] = "\N{LARGE YELLOW SQUARE}"
                points += 0.5
                unused.remove(guess_awakening.awoken_skill_id)
        return ["\n".join(["".join(awakes), "".join(feedback)]), points]

    async def get_other_info_line(self, ctx, monster, guess_monster):
        points = 0
        line1 = []
        line1.append(get_rarity_emoji(guess_monster.rarity))
        if monster.rarity == guess_monster.rarity:
            line1.append("\N{WHITE HEAVY CHECK MARK} | ")
            points += 1
        elif guess_monster.rarity > monster.rarity:
            line1.append("\N{DOWNWARDS BLACK ARROW}\N{VARIATION SELECTOR-16} | ")
        else:
            line1.append("\N{UPWARDS BLACK ARROW}\N{VARIATION SELECTOR-16} | ")
        for type in guess_monster.types:
            line1.append(get_type_emoji(type))
            if type in monster.types:
                points += 1
                line1.append("\N{WHITE HEAVY CHECK MARK} ")
            else:
                line1.append("\N{CROSS MARK} ")
        line1.append(" | Sell MP: ")
        line1.append('{:,}'.format(guess_monster.sell_mp))
        if guess_monster.sell_mp == monster.sell_mp:
            line1.append("\N{WHITE HEAVY CHECK MARK}")
            points += 1
        elif guess_monster.sell_mp > monster.sell_mp:
            line1.append("\N{DOWNWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}")
        else:
            line1.append("\N{UPWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}")

        return ["".join(line1), points]

    # i don't know if i should edit tsutils stuff
    async def get_embed_user_conf(self, ctx, embed,
                                  yes_emoji: SendableEmoji = YES_EMOJI, no_emoji: SendableEmoji = NO_EMOJI,
                                  timeout: int = 10, force_delete: Optional[bool] = None, show_feedback: bool = False) \
            -> Literal[True, False, None]:
        msg = await ctx.send(embed=embed)
        asyncio.create_task(msg.add_reaction(yes_emoji))
        asyncio.create_task(msg.add_reaction(no_emoji))

        def check(reaction, user):
            return (str(reaction.emoji) in [yes_emoji, no_emoji] and
                    user.id == ctx.author.id and reaction.message.id == msg.id)

        ret = False
        try:
            r, u = await ctx.bot.wait_for('reaction_add', check=check, timeout=timeout)
            if r.emoji == yes_emoji:
                ret = True
        except asyncio.TimeoutError:
            ret = None

        do_delete = force_delete
        if do_delete is None:
            do_delete = await get_user_preference(ctx.bot, ctx.author, 'delete_confirmation', unloaded_default=True)

        if do_delete:
            try:
                await msg.delete()
            except discord.Forbidden:
                pass

            if show_feedback:
                if ret is True:
                    await ctx.react_quietly(yes_emoji)
                elif ret is False:
                    await ctx.react_quietly(no_emoji)
        else:
            if ret is not True:
                await msg.remove_reaction(yes_emoji, ctx.me)
            if ret is not False:
                await msg.remove_reaction(no_emoji, ctx.me)

        return ret
