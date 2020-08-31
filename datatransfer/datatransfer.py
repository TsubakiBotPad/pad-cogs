import json
import os
import re
import base64
import io

import discord
from redbot.core import checks, data_manager, commands
from redbot.core.utils.chat_formatting import inline, box, pagify

class DataTransfer(commands.Cog):
    """Transfer cog data."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        """
        self._import = bot.get_cog("Alias").alias.command(name="import")(self._import)
        self.export = bot.get_cog("Alias").alias.command()(self.export)
        """

    @commands.group(name="export")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _export(self, ctx):
        """Data Export Utils"""

    @commands.group(name="import")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _import(self, ctx):
        """Data Import Utils"""

    @_import.command(name="alias")
    async def import_alias(self, ctx):
        if not ctx.message.attachments:
            await ctx.send(inline("Please attatch the .enc file retrieved from export function."))
            return
        try:
            data = json.loads(base64.b64decode(await ctx.message.attachments[0].read()).decode())

            for k,v in data.items():
                await self.bot.get_cog("Alias").config.guild(ctx.guild).set_raw(k, value=v)

            await self.bot.get_cog("Core").reload(ctx, "alias")
            await ctx.send(inline("Done."))
        except Exception as e:
            print(e)
            await ctx.send(inline("Invalid file."))

    @_export.command(name="alias")
    async def export_alias(self, ctx):
        raw_data = (await self.bot.get_cog("Alias").config.all_guilds())[ctx.guild.id]
        data = base64.b64encode(json.dumps(raw_data).encode())
        await ctx.send(file=discord.File(io.BytesIO(data), "alias_settings.enc"))

    @_import.command(name="customcom", aliases=["cc", "customcommands", "customcommand"])
    async def import_customcommand(self, ctx):
        if not ctx.message.attachments:
            await ctx.send(inline("Please attatch the .enc file retrieved from export function."))
            return
        try:
            data = json.loads(base64.b64decode(await ctx.message.attachments[0].read()).decode())

            for k,v in data.items():
                await self.bot.get_cog("CustomCommands").config.guild(ctx.guild).set_raw(k, value=v)

            await self.bot.get_cog("Core").reload(ctx, "customcom")
            await ctx.send(inline("Done."))
        except Exception as e:
            print(e)
            await ctx.send(inline("Invalid file."))

    @_export.command(name="customcom", aliases=["cc", "customcommands", "customcommand"])
    async def export_customcommand(self, ctx):
        raw_data = (await self.bot.get_cog("CustomCommands").config.all_guilds())[ctx.guild.id]
        data = base64.b64encode(json.dumps(raw_data).encode())
        await ctx.send(file=discord.File(io.BytesIO(data), "cc_settings.enc"))

    @_import.command(name="memes", aliases=["meme"])
    async def import_meme(self, ctx):
        if not ctx.message.attachments:
            await ctx.send(inline("Please send the .enc file retrieved from export function."))
            return
        try:
            data = json.loads(base64.b64decode(await ctx.message.attachments[0].read()).decode())
            self.bot.get_cog("Memes").settings.bot_settings['configs'][ctx.guild.id] = data['configs']
            self.bot.get_cog("Memes").c_commands[ctx.guild.id] = data['commands']
            json.dump(self.bot.get_cog("Memes").c_commands, open(self.bot.get_cog("Memes").file_path, 'w+'))
            await ctx.send(inline("Done."))
        except Exception as e:
            print(e)
            await ctx.send(inline("Invalid file."))

    @_export.command(name="memes", aliases=["meme"])
    async def export(self, ctx):
        raw_data = {
            'configs': self.bot.get_cog("Memes").settings.bot_settings['configs'].get(ctx.guild.id, {}),
            'commands': self.bot.get_cog("Memes").c_commands[ctx.guild.id],
        }
        data = base64.b64encode(json.dumps(raw_data).encode())
        await ctx.send(file=discord.File(io.BytesIO(data), "meme_settings.enc"))
