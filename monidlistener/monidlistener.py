import re
from io import BytesIO
from typing import TYPE_CHECKING

from redbot.core import Config, checks, commands
from tsutils.tsubaki.monster_header import MonsterHeader


if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.monster_graph import MonsterGraph


class MonIdListener(commands.Cog):
    """Monster Name from ID"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=10100779)
        self.config.register_channel(enabled=False)

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    @commands.Cog.listener('on_message')
    async def on_message(self, message):
        channel = message.channel
        content = message.content
        content = re.sub(r'297', '', content)
        if not await self.config.channel(channel).enabled():
            return
        if message.guild is None:  # dms
            return
        if message.author == self.bot.user:  # dont reply to self
            return
        if await self.is_command(message):  # skip commands
            return
        dbcog = self.bot.get_cog("DBCog")
        if dbcog is None:
            await channel.send("Error: DBCog Cog not loaded. Please alert a bot owner.")
            return
        if re.search(r'\b\d{3}[ -,]{0,2}\d{3}[ -,]{0,2}\d{3}\b', content):  # friend code
            return
        if "+" in content or "plus" in content:
            return
        if re.search(r'\b\d{3,4}\b', content):
            matches = re.findall(r'\b\d{3,4}\b', content)
            ret = ""
            for i in matches:
                if i == "100":  # skip when people say "is 100 mp or over" ~~and ryan's posts~~
                    continue
                m: "MonsterModel" = dbcog.get_monster(int(i))
                if m is None:  # monster not found
                    continue
                dbcog.database.graph: "MonsterGraph"
                if m.sell_mp < 100:
                    tradeable_text = ''
                else:
                    evo_gem_text = ''
                    if m.evo_gem_id is not None:
                        evo_gem: "MonsterModel" = dbcog.get_monster(m.evo_gem_id)
                        if evo_gem.sell_mp < 100:
                            evo_gem_text = ', but it has a tradable evo gem!'
                        else:
                            evo_gem_text = ', and its evo gem is also not tradable'

                    tradeable_text = " (untradable{})".format(evo_gem_text)

                ret += "{}{}\n".format(
                    MonsterHeader.text_with_emoji(m),
                    tradeable_text
                )
            if ret != "":
                await channel.send(ret)

    @commands.group(aliases=['monidlistener'])
    async def midlistener(self, ctx):
        """Commands pertaining to monster id lookup"""

    @midlistener.command()
    @checks.admin_or_permissions(manage_messages=True)
    async def enable(self, ctx):
        """Enable monster ID listener in this channel"""
        await self.config.channel(ctx.channel).enabled.set(True)
        await ctx.send("Enabled monster ID listener in this channel.")

    @midlistener.command()
    @checks.admin_or_permissions(manage_messages=True)
    async def disable(self, ctx):
        """Disable monster ID listener in this channel"""
        await self.config.channel(ctx.channel).enabled.set(False)
        await ctx.send("Disabled monster ID listener in this channel.")

    async def is_command(self, msg):
        prefixes = await self.bot.get_valid_prefixes()
        for p in prefixes:
            if msg.content.startswith(p):
                return True
        return False

    @commands.command(aliases=['tradable'])
    async def tradeable(self, ctx, *, query: str):
        """Look up if a card is tradeable"""
        dbcog = self.bot.get_cog("DBCog")
        monster = await dbcog.find_monster(query)
        if monster is None: 
            await ctx.send("Sorry, your query `" + query + "` didn't match any results :(")
            return

        if monster.sell_mp < 100:
            ret = "\t\t✅ This card is tradable!"
        else: 
            base_flag = False # Track other form tradability
            gem_flag = False  # Track evo gem tradability

            base_monster = dbcog.get_monster(monster.base_evo_id) 
            if base_monster.sell_mp < 100:
                base_flag = True

            if monster.evo_gem_id is not None:
                evo_gem: "MonsterModel" = dbcog.get_monster(monster.evo_gem_id)
                if evo_gem.sell_mp < 100:
                    gem_flag = True
            
            ret = (f"\t\t{'⁉️' if base_flag or gem_flag else '❌'} This card is **not tradable**.")
            if base_flag:
                ret += "\n\t\t\t\t✅ Other forms of this card are tradable."
            if gem_flag:
                ret += "\n\t\t\t\t✅ Evo gem for this card is tradable."
            elif monster.evo_gem_id is not None:
                ret += "\n\t\t\t\t❌ Evo gem for this card is not tradable."

        await ctx.send("{}\n{}".format(
            MonsterHeader.text_with_emoji(monster), ret))
