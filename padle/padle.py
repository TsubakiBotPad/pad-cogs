import discord
import datetime
import random
import asyncio

from typing import List, Literal, Optional
from redbot.core import Config, commands
from math import ceil

# from dbcog.monster_graph import MonsterGraph # used for creating the filter
from dbcog.dbcog import DBCog
from tsutils.tsubaki.custom_emoji import get_awakening_emoji, get_rarity_emoji, get_type_emoji, get_emoji
from tsutils.tsubaki.links import MonsterImage, MonsterLink
from tsutils.tsubaki.monster_header import MonsterHeader

from tsutils.cogs.userpreferences import get_user_preference
from tsutils.helper_functions import conditional_iterator
from tsutils.user_interaction import get_user_confirmation
from tsutils.emoji import NO_EMOJI, SendableEmoji, YES_EMOJI

from discordmenu.embed.components import EmbedThumbnail, EmbedMain
from discordmenu.embed.view import EmbedView
from redbot.core.utils.menus import (
    menu,
    next_page,
    prev_page,
    start_adding_reactions
)


class PADle(commands.Cog):
    """PADle"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=123456789)
        self.config.register_user(guesses=[], start=False, done=False, score=[], editID="", channelID="", embedText=[])
        self.config.register_global(padleToday=1, storedDay=0, numDays=0, subs=[], allScores=[], saveDailyScores=[])

        self._daily_padle_loop = bot.loop.create_task(self.generatePadle())

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
        await ctx.send("- PADle is similar to Wordle, except for PAD cards.\n"
                       "- You have infinite tries to guess the hidden PAD card (chosen from a list "
                       "of more-well known monsters). Everyone is trying to guess the same PAD card. "
                       "With each guess, you are given feedback as to how similar the two cards are, "
                       "including comparing the awakenings, rarity, typings, attributes, and monster "
                       "point sell value.\n- A new PADle is available every day. Use `^padle start` to begin!")

    @padle.command(aliases=["subscribe", "togglesub"])
    async def togglesubscribe(self, ctx):
        """Toggles daily notifications of new PADles"""
        subbedUsers = await self.config.subs()
        if ctx.author.id in subbedUsers:
            await ctx.send("You will no longer recieve notifications of new PADles.")
            async with self.config.subs() as subs:
                subs.remove(ctx.author.id)
            return
        await ctx.send("You will now recieve notifications of new PADles.")
        async with self.config.subs() as subs:
            subs.append(ctx.author.id)

    @padle.command()
    async def start(self, ctx):
        """Start a game of PADle"""
        if(ctx.guild is not None):
            await ctx.send("You can only play PADle in DMs!")
            return
        if(await self.config.user(ctx.author).done()):
            await ctx.send("You have already finished today's PADle!")
            return
        if(await self.config.user(ctx.author).start()):
            await ctx.send("You have already started a game!")
            return
        confirmation = await get_user_confirmation(ctx, "Start today's (#{}) PADle game?".format(
            await self.config.numDays()), timeout=30, force_delete=False, show_feedback=True)
        if not confirmation or await self.config.user(ctx.author).start():
            if confirmation is None:
                await ctx.send("Confirmation timeout.")
            return

        await self.config.user(ctx.author).start.set(True)
        em = discord.Embed(title="PADle #{}".format(await self.config.numDays()), type="rich",
                           description="Guess a card with `^padle guess <card>`!\nIf you give up, use `^padle giveup`.")
        message = await ctx.send(embed=em)
        await self.config.user(ctx.author).editID.set(message.id)
        await self.config.user(ctx.author).channelID.set(ctx.channel.id)
        await self.config.user(ctx.author).embedText.set([])

    @padle.command(aliases=["stats"])
    async def globalstats(self, ctx):
        """Gives global stats on today's PADle"""
        stats = await self.config.allScores()
        giveups = 0
        completes = 0
        average = 0
        for item in stats:
            if item == "X":
                giveups += 1
            else:
                completes += 1
                average += int(item)
        embed = discord.Embed(title="PADle #{} Stats".format(await self.config.numDays()), type="rich")
        if completes == 0:
            embed.description = ("**Total Wins**: {}\n**Total Losses**: {}\n**Win Rate**: 0%\n"
                                 "**Average Guess Count**: 0").format(completes, giveups)
        else:
            embed.description = ("**Total Wins**: {}\n**Total Losses**: {}\n**Win Rate**: {:.2%}\n"
                                 "**Average Guess Count**: {:.2f}").format(completes, giveups,
                                                                           completes / (completes + giveups),
                                                                           (average / completes))
        await ctx.send(embed=embed)

    # @padle.command()
    # @commands.is_owner()
    # async def fullreset(self, ctx):
    #     """Resets all stats and information."""
    #     with open("./pad-cogs/padle/monsters.txt", "r") as f:
    #         monsters = f.readline().split(",")
    #         await self.config.padleToday.set(random.choice(monsters))

    #     await self.config.numDays.set(1)
    #     await self.config.subs.set([])
    #     await self.config.allScores.set([])
    #     await self.config.saveDailyScores.set([])
    #     allUsers = await self.config.all_users()
    #     for userid in allUsers:
    #         user = await self.bot.fetch_user(userid)
    #         await self.config.user(user).guesses.set([])
    #         # need to send message if a user is mid-game
    #         if(await self.config.user(user).start() and not await self.config.user(user).done()):
    #             await user.send("A full reset occured, the PADle expired.")
    #         await self.config.user(user).start.set(False)
    #         await self.config.user(user).done.set(False)
    #         await self.config.user(user).score.set([])
    #         await self.config.user(user).editID.set("")
    #         await self.config.user(user).channelID.set("")
    #         await self.config.user(user).embedText.set([])
    #     await ctx.tick()

    # this takes a long time to run
    # @padle.command()
    # async def filter(self, ctx):
    #     dbcog = await self.get_dbcog()
    #     mgraph = dbcog.database.graph
    #     final = []
    #     for i in range(0, 8800):
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
        if ctx.guild is not None:
            await ctx.send("You can only play PADle in DMs!")
            return
        if(not await self.config.user(ctx.author).start()):
            await ctx.send("You have not started the game of PADle yet, try `^padle start`!")
            return
        if(await self.config.user(ctx.author).done()):
            await ctx.send("You have already played today's PADle!")
            return
        dbcog = await self.get_dbcog()

        guessMonster = await dbcog.find_monster(guess, ctx.author.id)
        if guessMonster is None:
            await ctx.send("Monster not found, please try again.", delete_after=10)
            return False

        monsterEmbed = EmbedView(
            EmbedMain(
                title=MonsterHeader.menu_title(guessMonster).to_markdown(),
                description="Did you mean this monster?"),
            embed_thumbnail=EmbedThumbnail(
                MonsterImage.icon(guessMonster.monster_id))).to_embed()
        confirmation = await self.get_embed_user_conf(ctx, monsterEmbed, timeout=20)
        if not confirmation:
            if confirmation is None:
                await ctx.send("Confirmation timeout.", delete_after=10)
            if confirmation is False:
                await ctx.send("Please guess again.", delete_after=10)
            return
        if(not await self.config.user(ctx.author).start() and not await self.config.user(ctx.author).done()):
            # confirming after day change or after finished
            return
        points = 0
        async with self.config.user(ctx.author).guesses() as guesses:
            guesses.append(guessMonster.monster_id)
        monster = await dbcog.find_monster(str(await self.config.padleToday()), ctx.author.id)
        nameLine = await self.getNameLine(ctx, monster, guessMonster)
        otherLine = await self.getOtherLine(ctx, monster, guessMonster)
        awakesLine = await self.getAwakesLine(ctx, monster, guessMonster)
        data = [nameLine[0], otherLine[0], awakesLine[0]]
        points += nameLine[1] + otherLine[1] + awakesLine[1]

        async with self.config.user(ctx.author).embedText() as descr:
            descr.append("\n".join(data))
        embedTexts = await self.config.user(ctx.author).embedText()
        channel = self.bot.get_channel(await self.config.user(ctx.author).channelID())
        delMsg = await channel.fetch_message(await self.config.user(ctx.author).editID())
        await delMsg.delete()
        embed_pages = []
        embed_controls = {
            "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}": prev_page,
            "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}": next_page,
        }
        emojis = ["\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
                  "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}"]
        numPages = ceil(len(embedTexts) / 5)
        for pageNum in range(ceil(len(embedTexts) / 5)):
            embed = discord.Embed(title="Padle #{}".format(await self.config.numDays()), type="rich")
            for index, text in enumerate(embedTexts[:5]):
                embed.add_field(name="**Guess {}**:".format(index + 1 + pageNum * 5), value=text, inline=False)
            embed.set_footer(text="Page {}/{}".format((pageNum + 1), numPages))
            embedTexts = embedTexts[5:]
            embed_pages.append(embed)
        message = await ctx.send(embed=discord.Embed(title="Padle"))
        await self.config.user(ctx.author).editID.set(message.id)
        await self.config.user(ctx.author).channelID.set(ctx.channel.id)
        score = ":yellow_square:"
        if(guessMonster.monster_id == monster.monster_id):
            await ctx.send("You got the PADle in {} guesses! Use `^padle score` to share your score.".format(
                len(await self.config.user(ctx.author).guesses())))
            await self.config.user(ctx.author).done.set(True)
            async with self.config.allScores() as allScores:
                allScores.append(str(len(await self.config.user(ctx.author).guesses())))
            score = ":green_square:"
        else:
            if(points < 9):
                score = ":orange_square:"
            if(points < 5):
                score = ":red_square:"
        async with self.config.user(ctx.author).score() as scores:
            scores.append(score)
        start_adding_reactions(message, emojis)
        await menu(ctx, embed_pages, embed_controls, message=message, page=len(embed_pages) - 1, timeout=60 * 60)

    @padle.command()
    async def giveup(self, ctx):
        """Give up on today's PADle"""
        if ctx.guild is not None:
            await ctx.send("You can only play PADle in DMs!")
            return
        if(not await self.config.user(ctx.author).start()):
            await ctx.send("You have not started the game of PADle yet, try `^padle start`!")
            return
        if(await self.config.user(ctx.author).done()):
            await ctx.send("You have already played today's PADle!")
            return
        confirmation = await get_user_confirmation(ctx, "Are you sure you would like to give up?", timeout=20)
        dbcog = await self.get_dbcog()
        if not confirmation:
            if confirmation is None:
                await ctx.send("Confirmation timeout.", delete_after=10)
            return
        monster = await dbcog.find_monster(str(await self.config.padleToday()), ctx.author.id)
        await self.config.user(ctx.author).done.set(True)
        monsterEmbed = EmbedView(EmbedMain(title=MonsterHeader.menu_title(monster).to_markdown(),
                                           description="PADle #{}".format(await self.config.numDays()),
                                           url=MonsterLink.ilmina(monster)),
                                 embed_thumbnail=EmbedThumbnail(MonsterImage.icon(monster.monster_id))).to_embed()
        await ctx.send(embed=monsterEmbed)
        await ctx.send("Use `^padle score` to share your score!")
        async with self.config.user(ctx.author).score() as scores:
            scores.append(":x:")
        async with self.config.allScores() as allScores:
            allScores.append("X")

    @padle.command()
    async def score(self, ctx):
        """Share your PADle score"""
        if(await self.config.user(ctx.author).done()):
            score = await self.config.user(ctx.author).score()
            if ":x:" in score:
                if(ctx.guild is None):
                    msg = "PADle #{}: X".format(await self.config.numDays()) \
                        + "\n" + "".join(score)
                    await ctx.send(msg)
                    await ctx.send("*Hint: You can use the command `^padle score` anywhere "
                                   "and have Tsubaki automatically share your score for you!*")
                else:
                    await ctx.message.delete()
                    msg = ctx.author.mention + "'s PADle #{}: X".format(await self.config.numDays()) \
                        + "\n" + "".join(score)
                    await ctx.send(msg)
            else:
                if(ctx.guild is None):
                    msg = "PADle #{}: {}".format(await self.config.numDays(),
                                                 len(await self.config.user(ctx.author).guesses())) + "\n" + "".join(score)
                    await ctx.send(msg)
                    await ctx.send("*Hint: You can use the command `^padle score` anywhere "
                                   "and have Tsubaki automatically share your score for you!*")
                else:
                    await ctx.message.delete()
                    msg = ctx.author.mention + "'s PADle #{}: {}".format(
                        await self.config.numDays(), len(await self.config.user(ctx.author).guesses())) \
                        + "\n" + "".join(score)
                    await ctx.send(msg)
        else:
            await ctx.send("You have not done today's PADle yet!")

    async def generatePadle(self):
        async def is_day_change():
            curDay = datetime.datetime.now().day
            oldDay = await self.config.storedDay()
            if curDay != oldDay:
                await self.config.storedDay.set(curDay)
                return True

        await self.bot.wait_until_ready()
        # idk what x is but it wants it to be there
        async for x in conditional_iterator(is_day_change, poll_interval=10):
            try:
                with open("./pad-cogs/padle/monsters.txt", "r") as f:
                    monsters = f.readline().split(",")
                    await self.config.padleToday.set(random.choice(monsters))
                num = await self.config.numDays()
                await self.config.numDays.set(num + 1)
                allUsers = await self.config.all_users()
                # to be used at a later date...
                async with self.config.saveDailyScores() as saveDaily:
                    saveDaily.append(await self.config.allScores())
                await self.config.allScores.set([])
                for userid in allUsers:
                    user = await self.bot.fetch_user(userid)
                    await self.config.user(user).guesses.set([])
                    # need to send message if a user is mid-game
                    if(await self.config.user(user).start() and not await self.config.user(user).done()):
                        await user.send("The PADle expired; a new one is available.")
                    await self.config.user(user).start.set(False)
                    await self.config.user(user).done.set(False)
                    await self.config.user(user).score.set([])
                    await self.config.user(user).editID.set("")
                    await self.config.user(user).channelID.set("")
                    await self.config.user(user).embedText.set([])
                subbedUsers = await self.config.subs()
                for userid in subbedUsers:
                    user = await self.bot.fetch_user(userid)
                    await user.send("PADle #{} is now available!".format(await self.config.numDays()))
            except asyncio.CancelledError:
                pass

    async def getNameLine(self, ctx, monster, guessMonster):
        nameLine = []
        attr1 = guessMonster.attr1.name.lower()
        attr2 = guessMonster.attr2.name.lower()
        attrFeedback = []
        attrFeedback.append(":white_check_mark:" if attr1 == monster.attr1.name.lower() else ":x:")
        attrFeedback.append(":white_check_mark:" if attr2 == monster.attr2.name.lower() else ":x:")
        if(attr1 == monster.attr2.name.lower() and
           attr2 != monster.attr2.name.lower() and attr1 != monster.attr1.name.lower()):
            attrFeedback[0] = ":yellow_square:"
        if(attr2 == monster.attr1.name.lower() and
           attr2 != monster.attr2.name.lower() and attr1 != monster.attr1.name.lower()):
            attrFeedback[1] = ":yellow_square:"
        nameLine.append(get_emoji("orb_{}".format(attr1)))
        nameLine.append(attrFeedback[0] + " / ")
        nameLine.append(get_emoji("orb_{}".format(attr2)))
        nameLine.append(attrFeedback[1] + " ")
        nameLine.append("[" + str(guessMonster.monster_id) + "] ")
        nameLine.append(guessMonster.name_en)
        points = (1 if attr1 == monster.attr1.name.lower() else 0) + (1 if attr2 == monster.attr2.name.lower() else 0)
        return ["".join(nameLine), points]

    async def getAwakesLine(self, ctx, monster, guessMonster):
        awakes = []
        unused = []
        feedback = []
        points = 0
        for index, guessAwake in enumerate(guessMonster.awakenings[:9]):
            awakes.append(get_awakening_emoji(guessAwake.awoken_skill_id, guessAwake.name))
            if(index < len(monster.awakenings) and
               monster.awakenings[index].awoken_skill_id == guessAwake.awoken_skill_id):
                feedback.append(":white_check_mark:")
                points += 1
            else:
                feedback.append(":x:")
                if index < len(monster.awakenings):
                    unused.append(monster.awakenings[index].awoken_skill_id)
        for index, guessAwake in enumerate(guessMonster.awakenings[:9]):
            if guessAwake.awoken_skill_id in unused and feedback[index] != ":white_check_mark:":
                feedback[index] = ":yellow_square:"
                points += 0.5
                unused.remove(guessAwake.awoken_skill_id)
        return ["\n".join(["".join(awakes), "".join(feedback)]), points]

    async def getOtherLine(self, ctx, monster, guessMonster):
        points = 0
        line1 = []
        line1.append(get_rarity_emoji(guessMonster.rarity))
        if monster.rarity == guessMonster.rarity:
            line1.append(":white_check_mark: | ")
            points += 1
        elif guessMonster.rarity > monster.rarity:
            line1.append(":arrow_down: | ")
        else:
            line1.append(":arrow_up: | ")
        for type in guessMonster.types:
            line1.append(get_type_emoji(type))
            if type in monster.types:
                points += 1
                line1.append(":white_check_mark: ")
            else:
                line1.append(":x: ")
        line1.append(" | Sell MP: ")
        line1.append('{:,}'.format(guessMonster.sell_mp))
        if guessMonster.sell_mp == monster.sell_mp:
            line1.append(":white_check_mark:")
            points += 1
        elif guessMonster.sell_mp > monster.sell_mp:
            line1.append(":arrow_down:")
        else:
            line1.append(":arrow_up:")

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
