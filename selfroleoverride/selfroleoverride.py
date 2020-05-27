import json
import re
import discord.utils
import asyncio

from ply import lex
from redbot.core import checks, Config
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, pagify

class SelfRoleConverterOverride(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> discord.Role:
        admin = ctx.command.cog.bot.get_cog("Admin")
        if admin is None:
            raise commands.BadArgument("The Admin cog is not loaded.")

        selfroles = await admin.config.guild(ctx.guild).selfroles()
        role_converter = commands.RoleConverter()

        pool = []
        for rid in selfroles:
            role = ctx.guild.get_role(rid)
            if role is None:
                continue
            if role.name.lower() == arg.lower():
                pool.append(role)
        if len(pool) == 0:
            role = await role_converter.convert(ctx, arg)

        else:
            if len(pool) > 1:
                await ctx.send("This selfrole has more than one capitalization"
                           "possibilities.  Please inform a moderator.")
            role = pool[0]



        if role.id not in selfroles:
            raise commands.BadArgument("The provided role is not a valid selfrole.")
        return role

class SelfRoleOverride(commands.Cog):
    """Overrides of builtin commands"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.old_cmds = []
        for cmd in self.__cog_commands__:
            old_cmd = bot.get_command(cmd.name)
            if old_cmd:
                bot.remove_command(old_cmd.name)
                self.old_cmds.append(old_cmd)

    def cog_unload(self):
        for cmd in self.old_cmds:
            try:
                self.bot.remove_command(cmd.name)
            except:
                pass
            self.bot.add_command(cmd)


    @commands.guild_only()
    @commands.group()
    async def selfrole(self, ctx: commands.Context):
        """Apply selfroles."""
        pass

    @selfrole.command(name="add")
    async def selfrole_add(self, ctx: commands.Context, *, selfrole: SelfRoleConverterOverride):
        """
        Add a selfrole to yourself.

        Server admins must have configured the role as user settable.
        """
        self = self.bot.get_cog("Admin")
        if self is None:
            await ctx.send("Admin cog not loaded.")

        await self._addrole(ctx, ctx.author, selfrole, check_user=False)

    @selfrole.command(name="remove")
    async def selfrole_remove(self, ctx: commands.Context, *, selfrole: SelfRoleConverterOverride):
        """
        Remove a selfrole from yourself.

        Server admins must have configured the role as user settable.
        """
        self = self.bot.get_cog("Admin")
        if self is None:
            await ctx.send("Admin cog not loaded.")

        await self._removerole(ctx, ctx.author, selfrole, check_user=False)

    @selfrole.command(name="list")
    async def selfrole_list(self, ctx: commands.Context):
        """
        Lists all available selfroles.
        """
        self = self.bot.get_cog("Admin")
        if self is None:
            await ctx.send("Admin cog not loaded.")

        selfroles = await self._valid_selfroles(ctx.guild)
        fmt_selfroles = "\n".join(["+ " + r.name for r in selfroles])

        if not fmt_selfroles:
            await ctx.send("There are currently no selfroles.")
            return

        msg = _("Available Selfroles:\n{selfroles}").format(selfroles=fmt_selfroles)
        await ctx.send(box(msg, "diff"))
