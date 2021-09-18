import time
from datetime import datetime, timedelta, timezone
from typing import Any, TYPE_CHECKING

from redbot.core import Config, commands
from tsutils.cog_mixins import CogMixin
from tsutils.user_interaction import get_user_confirmation

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
        self.config.register_user(opted_in=False, accounts=1)

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

    @adpem.group(usage="<pull1>, <pull2>, <pull3>, <pull4>", invoke_without_command=True)
    @opted_in(True)
    async def report(self, ctx, *, pulls):
        """Report a command or opt-in. """
        await self.report_at_time(ctx, pulls, self.midnight())

    @adpem.group(usage="<pull1>, <pull2>, <pull3>, <pull4>", invoke_without_command=True)
    @opted_in(True)
    async def reportyesterday(self, ctx, *, pulls):
        """Report yesterday's rolls"""
        await self.report_at_time(ctx, pulls, self.midnight() - (24 * 60 * 60))

    async def report_at_time(self, ctx, pulls, midnight):
        if not await self.config.user(ctx.author).opted_in():
            return await ctx.send(f"You need to opt in first via `{ctx.prefix}{' '.join(ctx.invoked_parents)} optin`")

        if len(pulls := pulls.split(',')) != 4:
            return await ctx.send("Make sure to supply all 4 rolls, and make sure not to put commas in their names.")

        dbcog: Any = ctx.bot.get_cog("DBCog")
        pdicog: Any = ctx.bot.get_cog("PadInfo")
        if dbcog is None or pdicog is None:
            return await ctx.send("Required cogs not loaded. Please alert a bot owner.")
        await dbcog.wait_until_ready()

        if not await self.assert_ready(ctx, midnight):
            return

        monsters = [await dbcog.find_monster('vem ' + pull.strip())
                    for pull in pulls]
        if not all(monsters):
            unknown = '\n\t'.join(s for s, m in zip(pulls, monsters) if m is None)
            return await ctx.send(f"Not all monsters were valid.  The following could not be processed:\n\t{unknown}")

        def get_vem_evo(mon: "MonsterModel") -> "MonsterModel":
            return {m for m in dbcog.database.graph.get_alt_monsters(mon) if m.in_vem}.pop()

        correct_evos = [get_vem_evo(m) for m in monsters]

        check = '\n\t'.join(pdicog.monster_header.fmt_id_header(m, use_emoji=True).to_markdown()
                            for m in correct_evos)
        if not await get_user_confirmation(ctx, f"Are these monsters correct?\n\t{check}",
                                           timeout=30, force_delete=False, show_feedback=True):
            return

        await self.add_roll(ctx, [m.monster_id for m in correct_evos])

    @report.command()
    async def skip(self, ctx):
        """Mark that you skipped your pulls today"""
        if not await self.assert_ready(ctx, self.midnight()):
            return
        await self.add_roll(ctx, "Skipped")

    @report.command()
    async def forgot(self, ctx):
        """Mark that you forgot your pulls today"""
        if not await self.assert_ready(ctx, self.midnight()):
            return
        await self.add_roll(ctx, "Forgot")

    @reportyesterday.command(name="skip")
    async def y_skip(self, ctx):
        """Mark that you skipped your pulls yesterday"""
        if not await self.assert_ready(ctx, self.midnight() - (24 * 60 * 60)):
            return
        await self.add_roll(ctx, "Skipped")

    @reportyesterday.command(name="forgot")
    async def y_forgot(self, ctx):
        """Mark that you forgot your pulls yesterday"""
        if not await self.assert_ready(ctx, self.midnight() - (24 * 60 * 60)):
            return
        await self.add_roll(ctx, "Forgot")

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

        pulls = [v for uid, v, ts in await self.config.pulls()
                 if midnight < ts < midnight + (24 * 60 * 60) and uid == ctx.author.id]
        if not pulls:
            return await ctx.send("There are no logged pulls during the given time period.")

        pulltext = []
        for pull in pulls:
            if isinstance(pull, str):
                pulltext.append(pull)
            else:
                pulltext.append('\t' + '\n\t'.join(
                    pdicog.monster_header.fmt_id_header(dbcog.get_monster(mid), use_emoji=True).to_markdown()
                    for mid in pull)
                                )
        pulltext = '\n\n'.join(pulltext)

        if not await get_user_confirmation(ctx, f"Are you sure you want to remove the following pulls:\n\n{pulltext}",
                                           force_delete=False, show_feedback=True):
            return

        async with self.config.pulls() as pulls:
            for pull in pulls:
                if midnight < pull[2] < midnight + (24 * 60 * 60) and pull[0] == ctx.author.id:
                    pulls.remove(pull)
        await ctx.send("Your pulls have been deleted.")

    @adpem.command()
    @opted_in(False)
    async def optin(self, ctx):
        """Opt in to the data collection system"""
        if not await get_user_confirmation(ctx, "We take data integrity very seriously! Please remember to:"
                                                "\n\t\N{BULLET} write this text later!\n"
                                                "Do you agree?", show_feedback=True):
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

    async def assert_ready(self, ctx, midnight: float) -> bool:
        pulls = await self.config.pulls()
        numtoday = len([1 for uid, v, ts in pulls
                        if midnight < ts < midnight + (24 * 60 * 60) and uid == ctx.author.id])
        if numtoday >= await self.config.user(ctx.author).accounts():
            await ctx.send(f"You already reported {numtoday} times today, which is your current number of"
                           f" accounts for reporting. If you're rolling daily on more accounts than this,"
                           f" you may increase your number of accounts via"
                           f" `{ctx.prefix}{ctx.invoked_parents[0]} setaccounts`, however please keep in"
                           f" mind we're very worried about selection bias, so please only do this if you"
                           f" are actually going to report daily!")
            return False
        return True

    async def add_roll(self, ctx, values: Any):
        async with self.config.pulls() as pulls:
            pulls.append((ctx.author.id, values, time.time()))

    def midnight(self) -> float:
        return datetime.now(timezone(timedelta(hours=-8))).replace(hour=0, minute=0, second=0, microsecond=0) \
            .astimezone(timezone.utc).timestamp()
