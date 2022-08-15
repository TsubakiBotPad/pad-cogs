from collections import Counter
from datetime import datetime, timezone
from typing import Any

import time
from discord import Color
from discordmenu.emoji.emoji_cache import emoji_cache
from redbot.core import Config, commands
from redbot.core.bot import Red
from tsutils.cog_mixins import CogMixin
from tsutils.emoji import NO_EMOJI, char_to_emoji
from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.time import NA_TIMEZONE, NEW_DAY, get_last_time
from tsutils.tsubaki.monster_header import MonsterHeader
from tsutils.user_interaction import get_user_confirmation, get_user_reaction

from crowddata.mixins.adpem.menu.closable_embed import ClosableEmbedMenu
from crowddata.mixins.adpem.view.show_stats import ShowStatsView, ShowStatsViewProps

# This is the timestamp of the most recent AdPEM reset
LAST_RESET = datetime(year=2021, month=12, day=24).timestamp()


def opted_in(is_opted):
    async def check(ctx):
        if is_opted == await ctx.bot.get_cog("CrowdData").config.user(ctx.author).opted_in():
            return True
        if is_opted and len(ctx.invoked_parents) != 1:
            await ctx.send(f"You need to opt in first via `{ctx.prefix}{ctx.invoked_parents[0]} optin`")
        return False

    return commands.check(check)


class AdPEMStats(CogMixin):
    config: Config
    bot: Red

    def setup_self(self):
        self.config.register_global(pulls=[], valid_lengths=[4])
        self.config.register_user(opted_in=False, accounts=1, skipconf=False)

    async def red_get_data_for_user(self, *, user_id):
        num = len([p for p in await self.config.pulls() if p[0] == user_id])
        return f"You have {num} logged pulls."

    async def red_delete_data_for_user(self, *, requester, user_id):
        async with self.config.pulls() as pulls:
            for pull in pulls:
                if pull[0] == user_id:
                    pulls.remove(pull)
        await self.config.user_from_id(user_id).opted_in.set(False)

    @commands.group(aliases=['vem'])
    async def adpem(self, ctx):
        """Log data for data from the Video Egg Machine"""

    @adpem.group(usage="pull1, pull2, pull3, pull4", invoke_without_command=True)
    @opted_in(True)
    async def report(self, ctx, *, pulls):
        """Report a set of pulls or opt-in."""
        await self.report_at_time(ctx, pulls, 0)

    @adpem.group(usage="pull1, pull2, pull3, pull4", invoke_without_command=True)
    @opted_in(True)
    async def reportyesterday(self, ctx, *, pulls):
        """Report yesterday's pulls"""
        await self.report_at_time(ctx, pulls, 24 * 60 * 60)

    async def report_at_time(self, ctx, pulls, offset):
        pulls_split = pulls.split(',')
        # TODO: support sending pulls throughout the day, and just have a single max # of pulls
        if len(pulls_split) > max(await self.config.valid_lengths()):
            return await ctx.send(f"Please supply all of your pulls with commas in between them. You can use names or"
                                  f" numbers.\n\t"
                                  f"Valid input: `{ctx.prefix}adpem report 618, 3719, 3600, 3013, 618`\n\t"
                                  f"Valid input: `{ctx.prefix}adpem report Enoch, Facet, D Globe, B Super King, Facet`")

        dbcog: Any = ctx.bot.get_cog("DBCog")
        if dbcog is None:
            return await ctx.send("Required cogs not loaded. Please alert a bot owner.")
        await dbcog.wait_until_ready()

        if not await self.assert_ready(ctx, self.midnight() - offset):
            return

        monsters = [await dbcog.find_monster('inadpem ' + pull.strip())
                    for pull in pulls_split]

        if not all(monsters):
            unknown = '\n\t'.join(s for s, m in zip(pulls_split, monsters) if m is None)
            return await ctx.send(f"Not all monsters were valid. The following could not be processed:\n\t{unknown}")

        check = '\n\t'.join(MonsterHeader.menu_title(m, use_emoji=True).to_markdown()
                            for m in monsters)
        confirmation = await get_user_confirmation(ctx, f"Are these monsters correct?\n\t{check}",
                                                   timeout=30, force_delete=False, show_feedback=True)
        if not confirmation:
            if confirmation is None:
                await ctx.send(ctx.author.mention + " Submission timed out. Please resubmit and verify.")
            return

        await self.add_pull(ctx, [m.monster_id for m in monsters], time.time() - offset)

    @report.command()
    async def skip(self, ctx):
        """Mark that you skipped your pulls today"""
        await self.skipforgot(ctx, 'Skipped', 0)

    @report.command()
    async def forgot(self, ctx):
        """Mark that you forgot your pulls today"""
        await self.skipforgot(ctx, 'Forgot', 0)

    @reportyesterday.command(name="skip")
    async def y_skip(self, ctx):
        """Mark that you skipped your pulls yesterday"""
        await self.skipforgot(ctx, 'Skipped', 24 * 60 * 60)

    @reportyesterday.command(name="forgot")
    async def y_forgot(self, ctx):
        """Mark that you forgot your pulls yesterday"""
        await self.skipforgot(ctx, 'Forgot', 24 * 60 * 60)

    async def skipforgot(self, ctx, ptype: str, offset: int):
        if not await self.assert_ready(ctx, self.midnight() - offset):
            return
        if not await self.config.user(ctx.author).skipconf() and \
                not await get_user_confirmation(ctx, f"Are you sure you want to report that you {ptype.lower()}"
                                                     f" {'yesterday' if offset else 'today'}'s pulls on an account?"
                                                     f"", force_delete=False, show_feedback=True):
            return
        await self.add_pull(ctx, ptype, time.time() - offset)
        if await self.config.user(ctx.author).skipconf():
            await ctx.tick()

    @adpem.command()
    @opted_in(True)
    async def remove(self, ctx):
        """Remove all of today's pulls"""
        await self.remove_at_time(ctx, self.midnight())

    @adpem.command()
    @opted_in(True)
    async def removeyesterday(self, ctx):
        """Remove all of yesterday's pulls"""
        await self.remove_at_time(ctx, self.midnight() - (24 * 60 * 60))

    async def remove_at_time(self, ctx, midnight):
        dbcog: Any = ctx.bot.get_cog("DBCog")
        if dbcog is None:
            return await ctx.send("Required cogs not loaded. Please alert a bot owner.")
        await dbcog.wait_until_ready()

        pulls = [[uid, v, ts] for uid, v, ts in await self.config.pulls()
                 if midnight <= ts < midnight + (24 * 60 * 60) and uid == ctx.author.id]
        pulls = {char_to_emoji(str(c)): vs for c, vs in enumerate(pulls, 1)}
        if not pulls:
            return await ctx.send("There are no logged pulls during the given time period.")

        pulltext = []
        for c, (uid, pull, ts) in pulls.items():
            if isinstance(pull, str):
                pulltext.append(c + ' ' + pull)
            else:
                pulltext.append(c + '\n\t' + '\n\t'.join(
                    MonsterHeader.menu_title(dbcog.get_monster(mid), use_emoji=True).to_markdown()
                    for mid in pull)
                                )
        pulltext = '\n\n'.join(pulltext)

        chosen = await get_user_reaction(ctx, f"Which set of pulls would you like to remove?\n\n{pulltext}",
                                         *pulls.keys(), NO_EMOJI, force_delete=False, show_feedback=True)

        if chosen is None or chosen == NO_EMOJI:
            return

        async with self.config.pulls() as c_pulls:
            c_pulls.remove(pulls[chosen])
        await ctx.send("Your pulls have been removed.")

    @adpem.command(aliases=['option'])
    @opted_in(False)
    async def optin(self, ctx):
        """Opt in to the data collection system"""
        if not await get_user_confirmation(ctx, f"Thanks for participating in our data collection! We take selection"
                                                f" bias VERY seriously."
                                                f" (See: <https://en.wikipedia.org/wiki/Selection_bias>)"
                                                f" By participating, you are agreeing to report **every single pull"
                                                f" that you make, every single day**. If you only report SOME pulls,"
                                                f" then you are likely to forget your worse pulls and report only the"
                                                f" better pulls, which would bias our statistics towards the better"
                                                f" pulls and make us sad. {emoji_cache.get_by_name('blobsad')}"
                                                f"\n\nSo report all pulls and give us nice,"
                                                f" unbiased data! {emoji_cache.get_by_name('blobcheer')}"
                                                f"\n\nDo you agree?",
                                           force_delete=False, show_feedback=True, timeout=30):
            return
        await self.config.user(ctx.author).opted_in.set(True)

    @adpem.command()
    @opted_in(True)
    async def setaccounts(self, ctx, number_of_accounts: int):
        """Set how many accounts you'll be using with this cog"""
        if not (1 <= number_of_accounts <= 10):
            await ctx.send("You must have at most 10 accounts.")
        await self.config.user(ctx.author).accounts.set(number_of_accounts)
        await ctx.tick()

    @report.command()
    @opted_in(True)
    async def toggleskipconfirm(self, ctx):
        """Toggle if you want to confirm on skip/forgot"""
        await self.config.user(ctx.author).skipconf.set(not await self.config.user(ctx.author).skipconf())
        await ctx.send(f"You have {'dis' if await self.config.user(ctx.author).skipconf() else 'en'}abled confirmation"
                       f" for `skip` and `forgot`.")

    @reportyesterday.command(name="toggleskipconfirm")
    @opted_in(True)
    async def y_toggleskipconfirm(self, ctx):
        """Toggle if you want to confirm on skip/forgot"""
        await self.toggleskipconfirm(ctx)

    @adpem.group(name="config")
    @commands.is_owner()
    async def v_config(self, ctx):
        """Admin config"""
        pass

    @v_config.command()
    async def maxrolls(self, ctx, *lens: int):
        """Change the valid number of pulls.

        If inputting multiple, separate with spaces
        """
        await self.config.valid_lengths.set(lens)
        await ctx.tick()

    @adpem.command()
    async def showstats(self, ctx, *, query):
        dbcog: Any = ctx.bot.get_cog("DBCog")

        original_author_id = ctx.message.author.id

        if dbcog is None:
            return await ctx.send("Required cogs not loaded. Please alert a bot owner.")
        await dbcog.wait_until_ready()

        async with ctx.typing():
            query = '" "'.join(query.split())
            monsters, _ = await dbcog.find_monsters(f'inadpem "{query}"')
            if not monsters:
                return await ctx.send("No monsters matched that query.")

            pulls = await self.config.pulls()
            data = [(uid, ps, ts) for uid, ps, ts in pulls if not isinstance(ps, str) and ts > LAST_RESET]
            total = [dbcog.get_monster(p) for uid, ps, ts in data for p in ps]
            adj = [dbcog.get_monster(p) for uid, ps, ts in data if self.has_good_data(uid, pulls) for p in ps]
            you = [dbcog.get_monster(p) for uid, ps, ts in data if uid == ctx.author.id for p in ps]
            valid = {m for m in total if m in monsters}

        if not valid:
            return await ctx.send("No monsters matching that query have been pulled.")

        most_common = Counter(m for m in total if m in monsters).most_common(1)[0][0]
        menu = ClosableEmbedMenu.menu()
        props = ShowStatsViewProps(total, adj, you, valid, most_common)
        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, query)
        state = ClosableEmbedViewState(original_author_id, ClosableEmbedMenu.MENU_TYPE, query.replace('"', ''),
                                       query_settings, ShowStatsView.VIEW_TYPE, props)

        await menu.create(ctx, state)

    async def assert_ready(self, ctx, midnight: float) -> bool:
        pulls = await self.config.pulls()
        numtoday = len([1 for uid, v, ts in pulls
                        if midnight <= ts < midnight + (24 * 60 * 60) and uid == ctx.author.id])
        if numtoday >= await self.config.user(ctx.author).accounts():
            await ctx.send(f"You already reported {numtoday} times"
                           f" {'today' if midnight > time.time() - 24 * 60 * 60 else 'yesterday'}, which "
                           f"is your current number of accounts for reporting. If you're pulling daily on more"
                           f" accounts than this, you may increase your number of accounts via"
                           f" `{ctx.prefix}{ctx.invoked_parents[0]} setaccounts`, however please keep in"
                           f" mind we're very worried about selection bias, so please only do this if you"
                           f" are actually going to report daily!")
            return False
        return True

    async def add_pull(self, ctx, values: Any, at_time: float):
        async with self.config.pulls() as pulls:
            pulls.append((ctx.author.id, values, at_time))

    def has_good_data(self, uid: int, pulls):
        dbcog: Any = self.bot.get_cog("DBCog")

        udata = [d for d in pulls if d[0] == uid]
        if len([1 for uid, ps, t in udata if ps == "Forgot"]) / len(udata) > .3:
            return False
        if len(udata) <= 2:
            return False

        # upulls = [dbcog.get_monster(p) for u, ps, t in udata if isinstance(ps, list) for p in ps]
        # if len([m for m in upulls if dbcog.database.graph.monster_is_rem_evo(m)]) / len(upulls) > .5:
        #     return False

        return True

    @staticmethod
    def midnight() -> float:
        return get_last_time(NEW_DAY, NA_TIMEZONE).astimezone(timezone.utc).timestamp()
