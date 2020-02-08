import os
import re
import discord 

from redbot.core import commands

from redbot.core import checks
from redbot.core.utils.chat_formatting import pagify, box
from rpadutils.rpadutils import CogSettings


class PadBuilds(commands.Cog):
    """Custom PAD builds

    Creates commands used to display text"""

    def __init__(self, bot):
        self.bot = bot
        self.c_commands = PadBuildSettings("padbuilds")

    @commands.group(aliases=["build"])
    @commands.guild_only()
    async def builds(self, ctx):
        """PAD Builds management"""

    @builds.command(name="add")
    @checks.mod_or_permissions(administrator=True)
    async def cc_add(self, ctx, command: str, *, text):
        """Adds a PAD Build

        Example:
        [p]builds add buildname Text you want

        Builds can be enhanced with arguments:
        https://twentysix26.github.io/Red-Docs/red_guide_command_args/
        """
        server = ctx.guild
        command = command.lower()
        text = text.replace(u'\u200b', '')
        if command in self.bot.commands:
            await ctx.send("That is already a standard command.")
            return
        if server.id not in self.c_commands:
            self.c_commands.set_key(server.id, {})
        cmdlist = self.c_commands.get_key(server.id)
        if command not in cmdlist:
            cmdlist[command] = text
            self.c_commands.set_key(server.id, cmdlist)
            self.c_commands.save_settings()
            await ctx.send("PAD Build successfully added.")
        else:
            await ctx.send("This build already exists. Use "
                               "`{}builds edit` to edit it."
                               "".format(ctx.prefix))

    @builds.command(name="edit")
    @checks.mod_or_permissions(administrator=True)
    async def cc_edit(self, ctx, command: str, *, text):
        """Edits a PAD Build

        Example:
        [p]builds edit buildname Text you want
        """
        server = ctx.guild
        command = command.lower()
        text = text.replace(u'\u200b', '')
        if server.id in self.c_commands:
            cmdlist = self.c_commands.get_key(server.id)
            if command in cmdlist:
                cmdlist[command] = text
                self.c_commands.set_key(server.id, cmdlist)
                self.c_commands.save_settings()
                await ctx.send("PAD Build successfully edited.")
            else:
                await ctx.send("That build doesn't exist. Use "
                                   "`{}builds add` to add it."
                                   "".format(ctx.prefix))
        else:
            await ctx.send("There are no PAD Builds in this server."
                               " Use `{}builds add` to start adding some."
                               "".format(ctx.prefix))

    @builds.command(name="delete")
    @checks.mod_or_permissions(administrator=True)
    async def cc_delete(self, ctx, command: str):
        """Deletes a PAD Build

        Example:
        [p]builds delete buildname"""
        server = ctx.guild
        command = command.lower()
        if server.id in self.c_commands:
            cmdlist = self.c_commands.get_key(server.id)
            if command in cmdlist:
                cmdlist.pop(command, None)
                self.c_commands.set_key(server.id, cmdlist)
                self.c_commands.save_settings()
                await ctx.send("PAD Build successfully deleted.")
            else:
                await ctx.send("That command doesn't exist.")
        else:
            await ctx.send("There are no PAD Builds in this server."
                               " Use `{}builds add` to start adding some."
                               "".format(ctx.prefix))

    @builds.command(name="list")
    async def cc_list(self, ctx):
        """Shows PAD Builds list"""
        server = ctx.guild
        commands = self.c_commands.get_key(server.id, default = {})

        if not commands:
            await ctx.send("There are no PAD Builds in this server."
                               " Use `{}builds add` to start adding some."
                               "".format(ctx.prefix))
            return

        commands = ", ".join([ctx.prefix + c for c in sorted(commands)])
        commands = "PAD Builds:\n\n" + commands

        if len(commands) < 1500:
            await ctx.send(box(commands))
        else:
            for page in pagify(commands, delims=[" ", "\n"]):
                await ctx.author.send(box(page))

    @commands.Cog.listener("on_message")
    async def on_message(self, message):
        if len(message.content) < 2 or isinstance(message.channel, discord.abc.PrivateChannel):
            return

        server = message.guild
        prefix = await self.bot.get_prefix(message)
        prefix = prefix[0]

        if not prefix:
            return

        if server.id in self.c_commands:
            cmdlist = self.c_commands.get_key(server.id)
            cmd = message.content[len(prefix):]
            if cmd in cmdlist:
                cmd = cmdlist[cmd]
                cmd = self.format_cc(cmd, message)
                await message.channel.send(cmd)
            elif cmd.lower() in cmdlist:
                cmd = cmdlist[cmd.lower()]
                cmd = self.format_cc(cmd, message)
                await message.channel.send(cmd)

    def format_cc(self, command, message):
        results = re.findall("\{([^}]+)\}", command)
        for result in results:
            param = self.transform_parameter(result, message)
            command = command.replace("{" + result + "}", param)
        return command

    def transform_parameter(self, result, message):
        """
        For security reasons only specific objects are allowed
        Internals are ignored
        """
        raw_result = "{" + result + "}"
        objects = {
            "message": message,
            "author": message.author,
            "channel": message.channel,
            "server": message.guild
        }
        if result in objects:
            return str(objects[result])
        try:
            first, second = result.split(".")
        except ValueError:
            return raw_result
        if first in objects and not second.startswith("_"):
            first = objects[first]
        else:
            return raw_result
        return str(getattr(first, second, raw_result))


class PadBuildSettings(CogSettings):
    SETTINGS_FILE_NAME = "commands.json"

    def make_default_settings(self):
        return {}

    def get_key(self, key, **kwargs):
        if 'default' in kwargs:
            return self.bot_settings.get(key, kwargs['default']) 
        return self.bot_settings[key]

    def set_key(self, key, value):
        self.bot_settings[key] = value

    def del_key(self, key):
        del self.bot_settings[key]

    def __contains__(self, item):
        return item in self.bot_settings
