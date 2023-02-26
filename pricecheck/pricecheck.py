from io import BytesIO

from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import box, inline, pagify
from tsutils.cogs.globaladmin import auth_check

DISCLAIMER = "**Disclaimer**: This is Lumon's data. Use at your own discretion."

PC_TEXT = """{name}
 - Stamina Cost: {stam_cost}
 - Plus Point Value: {pp_val} ({points} 𝟤𝟫𝟩 Plus Points)

{foot}
"""


def rint(x, p):
    return str(round(x, p)).rstrip('0').rstrip('.')


class PriceCheck(commands.Cog):
    """A pricechecking cog for Lumon"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9213337337)
        self.config.register_global(pcs={})
        self.config.register_channel(dm=False)
        GADMIN_COG = self.bot.get_cog("GlobalAdmin")
        if GADMIN_COG:
            GADMIN_COG.register_perm("pcadmin")

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    @commands.group(invoke_without_command=True)
    async def pricecheck(self, ctx, *, query):
        """Displays pricing data for a tradable non-collab gem."""
        dbcog = self.bot.get_cog("DBCog")
        if dbcog is None:
            await ctx.send(inline("Error: Cog not loaded.  Please alert a bot owner."))
            return
        if "gem" not in query.lower():
            query += " gem"
        m = await dbcog.find_monster(query, ctx.author.id)
        if not m:
            await ctx.send("Monster not found.")
            return
        base_id = str(dbcog.database.graph.get_base_id(m))
        async with self.config.pcs() as pcs:
            if base_id not in pcs:
                if m.sell_mp < 100:
                    await ctx.send("{} does not have PC data.".format(m.name_en))
                else:
                    await ctx.send("{} is not tradable.".format(m.name_en))
                return
            sc, foot = pcs[base_id]
        pct = PC_TEXT.format(name=m.name_en,
                             stam_cost=rint(sc, 2),
                             pp_val=rint(sc * 83 / 50, 2),
                             points=rint(sc * 83 / 50 / 297, 2),
                             foot=foot)
        if await self.config.channel(ctx.channel).dm():
            await ctx.send(DISCLAIMER)
            for page in pagify(pct):
                await ctx.author.send(box(page.replace("'", "ʼ"), lang='q'))
        else:
            await ctx.send(DISCLAIMER)
            for page in pagify(pct):
                await ctx.send(box(page.replace("'", "ʼ"), lang='q'))

    @commands.group()
    @auth_check('pcadmin')
    async def pcadmin(self, ctx):
        """Creates custom commands for [p]pricecheck."""

    @pcadmin.command(aliases=['add'])
    async def set(self, ctx, stam_cost: float, *, query):
        """Adds stamina cost data to a card."""
        dbcog = self.bot.get_cog("DBCog")
        if dbcog is None:
            await ctx.send(inline("Error: Cog not loaded.  Please alert a bot owner."))
            return
        if "gem" not in query.lower():
            query += " gem"
        m = await dbcog.find_monster(query, ctx.author.id)
        if not m:
            await ctx.send("Monster not found.")
            return
        base_id = str(dbcog.database.graph.get_base_id(m))
        async with self.config.pcs() as pcs:
            foot = ""
            if base_id in pcs:
                foot = pcs[base_id][1]
            pcs[base_id] = (stam_cost, foot)
        await ctx.send(box("Set {} ({}) to {}".format(m.name_en, base_id, stam_cost)))

    @pcadmin.command(aliases=['addfooter', 'addfoot', 'setfoot'])
    async def setfooter(self, ctx, query, *, footer=""):
        """Adds notes regarding the stamina cost of a card."""
        dbcog = self.bot.get_cog('DBCog')
        if dbcog is None:
            await ctx.send(inline("Error: Cog not loaded.  Please alert a bot owner."))
            return
        if "gem" not in query.lower():
            query += " gem"
        m = await dbcog.find_monster(query, ctx.author.id)
        if not m:
            await ctx.send("Monster not found.")
            return
        base_id = str(dbcog.database.graph.get_base_id(m))
        async with self.config.pcs() as pcs:
            sc = -1
            if base_id in pcs:
                sc = pcs[base_id][0]
            pcs[base_id] = (sc, footer.strip('`'))
        await ctx.send(box("Set {} ({}) footer to '{}'".format(m.name_en, base_id, footer)))

    @pcadmin.command(aliases=['delete', 'del', 'rm'])
    async def remove(self, ctx, *, query):
        """Removes stamina cost data from a card."""
        dbcog = self.bot.get_cog('DBCog')
        if dbcog is None:
            await ctx.send(inline("Error: Cog not loaded.  Please alert a bot owner."))
            return
        if "gem" not in query.lower():
            query += " gem"
        m = await dbcog.find_monster(query, ctx.author.id)
        if not m:
            await ctx.send("Monster not found.")
            return
        async with self.config.pcs() as pcs:
            if str(dbcog.database.graph.get_base_id(m)) not in pcs:
                await ctx.send("{} does not have PC data.".format(m.name_en))
                return
            del pcs[str(dbcog.database.graph.get_base_id(m))]
        await ctx.send("Removed PC data from {}.".format(m.name_en))

    @pcadmin.command()
    async def setdmonly(self, ctx, value: bool = True):
        """Tells a channel to send [p]pricecheck in dms."""
        await self.config.channel(ctx.channel).dm.set(value)
        await ctx.tick()
