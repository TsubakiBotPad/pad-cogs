import re

import discord
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import inline, box, pagify

from tsutils import auth_check

PC_TEXT = """{name} - Stamina Cost: {stam_cost}

{name} - Plus Point Value: {pp_val}
({points} 297 Plus Points)

{foot}
"""


class PriceCheck(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9213337337)
        self.config.register_global(pcs={})
        self.config.register_channel(dm=False)
        self.bot.get_cog("GlobalAdmin").register_perm("pcadmin")

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
                await ctx.send("{} does not have PC data.".format(nm.name_na))
                return
            sc, foot = pcs[str(nm.base_monster_no)]
        pct = PC_TEXT.format(name = nm.name_na,
                             stam_cost = sc,
                             pp_val = sc*83/50,
                             points = sc*83/50/297,
                             foot = foot)
        if await self.config.channel(ctx.channel).dm():
            for page in pagify(pct):
                await ctx.author.send(box(page))
        else:
            for page in pagify(pct):
                await ctx.send(box(page))

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
        await ctx.send(box("Set {} ({}) to {}".format(nm.name_na, nm.base_monster_no, stam_cost)))

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
        await ctx.send(box("Set {} ({}) footer to '{}'".format(nm.name_na, nm.base_monster_no, footer)))

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
                await ctx.send("{} does not have PC data.".format(nm.name_na))
                return
            del pcs[str(nm.base_monster_no)]
        await ctx.send(inline("Removed PC data from {}.".format(nm.name_na)))

    @pcadmin.command(aliases=['set-demon-ly'])
    async def setdmonly(self, ctx, value: bool = True):
        """Tells a channel to send [p]pricecheck in dms."""
        await self.config.channel(ctx.channel).dm.set(value)
        await ctx.tick()
