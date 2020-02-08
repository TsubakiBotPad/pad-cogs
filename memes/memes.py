import os
import re
import json

import discord
from discord.ext import commands

from rpadutils.rpadutils import *
from rpadutils.rpadutils import CogSettings
from redbot.core import checks
from padinfo.padinfo import _validate_json

class Memes(commands.Cog):
    """Custom memes."""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/memes/commands.json"
        with open("data/memes/commands.json", "a+") as f:
            f.seek(0)
            self.c_commands = json.load(f)
        self.settings = MemesSettings("memes")

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def addmeme(self, ctx, command: str, *, text):
        """Adds a meme

        Example:
        [p]addmeme yourmeme Text you want

        Memes can be enhanced with arguments:
        https://twentysix26.github.io/Red-Docs/red_guide_command_args/
        """
        guild = ctx.guild
        command = command.lower()
        if command in self.bot.all_commands.keys():
            await ctx.send("That meme is already a standard command.")
            return
        if not guild.id in self.c_commands:
            self.c_commands[guild.id] = {}
        cmdlist = self.c_commands[guild.id]
        if command not in cmdlist:
            cmdlist[command] = text
            self.c_commands[guild.id] = cmdlist
            json.dump(self.c_commands, open(self.file_path, 'w+'))
            await ctx.send("Custom command successfully added.")
        else:
            await ctx.send("This command already exists. Use editmeme to edit it.")

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def editmeme(self, ctx, command: str, *, text):
        """Edits a meme

        Example:
        [p]editmeme yourcommand Text you want
        """
        guild = ctx.guild
        command = command.lower()
        if guild.id in self.c_commands:
            cmdlist = self.c_commands[guild.id]
            if command in cmdlist:
                cmdlist[command] = text
                self.c_commands[guild.id] = cmdlist
                json.dump(self.c_commands, open(self.file_path, 'w+'))
                await ctx.send("Custom command successfully edited.")
            else:
                await ctx.send("That command doesn't exist. Use addmeme [command] [text]")
        else:
            await ctx.send("There are no custom memes in this server. Use addmeme [command] [text]")

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def delmeme(self, ctx, command: str):
        """Deletes a meme

        Example:
        [p]delmeme yourcommand"""
        guild = ctx.guild
        command = command.lower()
        if guild.id in self.c_commands:
            cmdlist = self.c_commands[guild.id]
            if command in cmdlist:
                cmdlist.pop(command, None)
                self.c_commands[guild.id] = cmdlist
                json.dump(self.c_commands, open(self.file_path, 'w+'))
                await ctx.send("Custom meme successfully deleted.")
            else:
                await ctx.send("That meme doesn't exist.")
        else:
            await ctx.send("There are no custom memes in this server. Use addmeme [command] [text]")

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def setmemerole(self, ctx, rolename: str):
        """Sets the meme role

        Example:
        [p]setmemerole Regular"""

        role = get_role(ctx.message.guild.roles, rolename)
        self.settings.setPrivileged(ctx.guild.id, role.id)
        await ctx.send("done")

    @commands.command()
    @commands.guild_only()
    async def memes(self, ctx):
        """Shows custom memes list"""
        guild = ctx.guild
        if guild.id in self.c_commands and self.c_commands[guild.id]:
            cmdlist = self.c_commands[guild.id]
            i = 0
            msg = ["```Custom memes:\n"]
            for cmd in sorted([cmd for cmd in cmdlist.keys()]):
                if len(msg[i]) + len(ctx.prefix) + len(cmd) + 5 > 2000:
                    msg[i] += "```"
                    i += 1
                    msg.append("``` {}{}\n".format(ctx.prefix, cmd))
                else:
                    msg[i] += " {}{}\n".format(ctx.prefix, cmd)
            msg[i] += "```"
            for cmds in msg:
                await ctx.author.send(cmds)
        else:
            await ctx.send("There are no custom memes in this server. Use addmeme [command] [text]")

    @commands.Cog.listener('on_message')
    async def checkCC(self, message):
        if len(message.content) < 2 or isinstance(message.channel, discord.abc.PrivateChannel):
            return

        guild = message.guild
        prefix = await self.get_prefix(message)

        if not prefix:
            return

        # MEME CODE
        role_id = self.settings.getPrivileged(guild.id)
        if role_id is not None:
            role = get_role_from_id(self.bot, guild, role_id)
            if role not in message.author.roles:
                return

        # MEME CODE
        rpadutilsCog = self.bot.get_cog('RpadUtils')
        if guild.id in self.c_commands and rpadutilsCog.user_allowed(message):
            cmdlist = self.c_commands[guild.id]
            cmd = message.content[len(prefix):]
            if cmd in cmdlist.keys():
                cmd = cmdlist[cmd]
                cmd = self.format_cc(cmd, message)
                await message.channel.send(cmd)
            elif cmd.lower() in cmdlist.keys():
                cmd = cmdlist[cmd.lower()]
                cmd = self.format_cc(cmd, message)
                await message.channel.send(cmd)

    async def get_prefix(self, message):
        for p in await self.bot.get_prefix(message):
            if message.content.startswith(p):
                return p
        return False

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


def check_folders():
    if not os.path.exists("data/memes"):
        print("Creating data/memes folder...")
        os.makedirs("data/memes")


def check_files():
    f = "data/memes/commands.json"
    if not _validate_json(f):
        print("Creating empty commands.json...")
        json.dump({}, open(f, 'w+'))


class MemesSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'configs': {}
        }
        return config

    def guildConfigs(self):
        return self.bot_settings['configs']

    def getGuild(self, guild_id):
        configs = self.guildConfigs()
        if guild_id not in configs:
            configs[guild_id] = {}
        return configs[guild_id]

    def getPrivileged(self, guild_id):
        guild = self.getGuild(guild_id)
        return guild.get('privileged')

    def setPrivileged(self, guild_id, role_id):
        guild = self.getGuild(guild_id)
        guild['privileged'] = role_id
        self.save_settings()
