import discord
import re
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box, inline, pagify
from tsutils import auth_check

DISCLAIMER = "**Disclaimer**: This is Lumon's data. Use at your own discretion."

PC_TEXT = """{name}
 - Stamina Cost: {stam_cost}
 - Plus Point Value: {pp_val} ({points} 𝟤𝟫𝟩 Plus Points)

{foot}
"""

def rint(x, p):
    return str(round(x, p)).rstrip('0').rstrip('.')

class PriceCheck(commands.Cog):
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
        padinfo_cog = self.bot.get_cog('PadInfo')
        if padinfo_cog is None:
            await ctx.send(inline("Error: PadInfo Cog not loaded.  Please alert a bot owner."))
            return
        if "gem" not in query.lower():
            query += " gem"
        nm, err, debug_info = await padinfo_cog._findMonster(query)
        if not nm:
            await ctx.send(err)
            return
        async with self.config.pcs() as pcs:
            if str(nm.base_monster_no) not in pcs:
                await ctx.send("{} does not have PC data.".format(nm.name_en))
                return
            sc, foot = pcs[str(nm.base_monster_no)]
        pct = PC_TEXT.format(name=nm.name_na,
                             stam_cost=rint(sc, 2),
                             pp_val=rint(sc * 83 / 50, 2),
                             points=rint(sc * 83 / 50 / 297, 2),
                             foot=foot)
        if await self.config.channel(ctx.channel).dm():
            await ctx.send(DISCLAIMER)
            for page in pagify(pct):
                await ctx.author.send(box(page.replace("'","ʼ"), lang='py'))
        else:
            await ctx.send(DISCLAIMER)
            for page in pagify(pct):
                await ctx.send(box(page.replace("'","ʼ"), lang='py'))

    @commands.group()
    @auth_check('pcadmin')
    async def pcadmin(self, ctx):
        """Creates custom commands for [p]pricecheck."""

    @pcadmin.command(aliases=['add'])
    async def set(self, ctx, stam_cost: float, *, query):
        """Adds stamina cost data to a card."""
        padinfo_cog = self.bot.get_cog('PadInfo')
        if padinfo_cog is None:
            await ctx.send(inline("Error: PadInfo Cog not loaded.  Please alert a bot owner."))
            return
        if "gem" not in query.lower():
            query += " gem"
        nm, err, debug_info = await padinfo_cog._findMonster(query)
        if not nm:
            await ctx.send(err)
            return
        async with self.config.pcs() as pcs:
            foot = ""
            if str(nm.base_monster_no) in pcs:
                foot = pcs[str(nm.base_monster_no)][1]
            pcs[str(nm.base_monster_no)] = (stam_cost, foot)
        await ctx.send(box("Set {} ({}) to {}".format(nm.name_en, nm.base_monster_no, stam_cost)))

    @pcadmin.command(aliases=['addfooter', 'addfoot', 'setfoot'])
    async def setfooter(self, ctx, query, *, footer=""):
        """Adds notes regarding the stamina cost of a card."""
        padinfo_cog = self.bot.get_cog('PadInfo')
        if padinfo_cog is None:
            await ctx.send(inline("Error: PadInfo Cog not loaded.  Please alert a bot owner."))
            return
        if "gem" not in query.lower():
            query += " gem"
        nm, err, debug_info = await padinfo_cog._findMonster(query)
        if not nm:
            await ctx.send(err)
            return
        async with self.config.pcs() as pcs:
            sc = -1
            if str(nm.base_monster_no) in pcs:
                sc = pcs[str(nm.base_monster_no)][0]
            pcs[str(nm.base_monster_no)] = (sc, footer.strip('`'))
        await ctx.send(box("Set {} ({}) footer to '{}'".format(nm.name_en, nm.base_monster_no, footer)))

    @pcadmin.command(aliases=['delete', 'del', 'rm'])
    async def remove(self, ctx, *, query):
        """Removes stamina cost data from a card."""
        padinfo_cog = self.bot.get_cog('PadInfo')
        if padinfo_cog is None:
            await ctx.send(inline("Error: PadInfo Cog not loaded.  Please alert a bot owner."))
            return
        if "gem" not in query.lower():
            query += " gem"
        nm, err, debug_info = await padinfo_cog._findMonster(query)
        if not nm:
            await ctx.send(err)
            return
        async with self.config.pcs() as pcs:
            if str(nm.base_monster_no) not in pcs:
                await ctx.send("{} does not have PC data.".format(nm.name_en))
                return
            del pcs[str(nm.base_monster_no)]
        await ctx.send(inline("Removed PC data from {}.".format(nm.name_en)))

    @pcadmin.command(aliases=['set-demon-ly'])
    async def setdmonly(self, ctx, value: bool = True):
        """Tells a channel to send [p]pricecheck in dms."""
        await self.config.channel(ctx.channel).dm.set(value)
        await ctx.tick()
