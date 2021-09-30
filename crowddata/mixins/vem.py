import time
from datetime import datetime, timedelta, timezone
from typing import Any, TYPE_CHECKING

from discordmenu.emoji.emoji_cache import emoji_cache
from redbot.core import Config, commands
from tsutils.cog_mixins import CogMixin
from tsutils.emoji import NO_EMOJI, char_to_emoji
from tsutils.time import NA_TIMEZONE, ROLLOVER, get_last_time
from tsutils.user_interaction import get_user_confirmation, get_user_reaction

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


def opted_in(is_opted):
    async def check(ctx):
        return is_opted == await ctx.bot.get_cog("CrowdData").config.user(ctx.author).opted_in()

    return commands.check(check)


class VEM(CogMixin):
    config: Config

    def setup_self(self):
        self.config.register_global(pulls=[])
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
        if not await self.config.user(ctx.author).opted_in():
            return await ctx.send(f"You need to opt in first via `{ctx.prefix}{' '.join(ctx.invoked_parents)} optin`")

        if len(pulls := pulls.split(',')) != 4:
            return await ctx.send(f"Please supply all 4 pulls with commas in between them. You can use names or"
                                  f" numbers.\n\t"
                                  f"Valid input: `{ctx.prefix}adpem report 618, 3719, 3600, 3013`\n\t"
                                  f"Valid input: `{ctx.prefix}adpem report Enoch, Facet, D Globe, B Super King`")

        dbcog: Any = ctx.bot.get_cog("DBCog")
        pdicog: Any = ctx.bot.get_cog("PadInfo")
        if dbcog is None or pdicog is None:
            return await ctx.send("Required cogs not loaded. Please alert a bot owner.")
        await dbcog.wait_until_ready()

        if not await self.assert_ready(ctx, self.midnight() - offset):
            return

        monsters = [await dbcog.find_monster('vem ' + pull.strip())
                    for pull in pulls]
        if not all(monsters):
            unknown = '\n\t'.join(s for s, m in zip(pulls, monsters) if m is None)
            return await ctx.send(f"Not all monsters were valid. The following could not be processed:\n\t{unknown}")

        def get_vem_evo(mon: "MonsterModel") -> "MonsterModel":
            return {m for m in dbcog.database.graph.get_alt_monsters(mon) if m.in_vem}.pop()

        correct_evos = [get_vem_evo(m) for m in monsters]

        check = '\n\t'.join(pdicog.monster_header.fmt_id_header(m, use_emoji=True).to_markdown()
                            for m in correct_evos)
        if not await get_user_confirmation(ctx, f"Are these monsters correct?\n\t{check}",
                                           timeout=30, force_delete=False, show_feedback=True):
            return

        await self.add_pull(ctx, [m.monster_id for m in correct_evos], time.time() - offset)

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
        pdicog: Any = ctx.bot.get_cog("PadInfo")
        if dbcog is None or pdicog is None:
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
                    pdicog.monster_header.fmt_id_header(dbcog.get_monster(mid), use_emoji=True).to_markdown()
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

    @staticmethod
    def midnight() -> float:
        return get_last_time(ROLLOVER, NA_TIMEZONE).astimezone(timezone.utc).timestamp()
