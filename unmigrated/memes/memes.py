import os
import re

import discord
from discord.ext import commands

from __main__ import user_allowed, send_cmd_help

from .rpadutils import *
from .rpadutils import CogSettings
from .utils import checks
from .utils.dataIO import dataIO


class Memes:
    """Custom memes."""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/memes/commands.json"
        self.c_commands = dataIO.load_json(self.file_path)
        self.settings = MemesSettings("memes")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def addmeme(self, ctx, command: str, *, text):
        """Adds a meme

        Example:
        [p]addmeme yourmeme Text you want

        Memes can be enhanced with arguments:
        https://twentysix26.github.io/Red-Docs/red_guide_command_args/
        """
        server = ctx.message.server
        command = command.lower()
        if command in self.bot.commands.keys():
            await self.bot.say("That meme is already a standard command.")
            return
        if not server.id in self.c_commands:
            self.c_commands[server.id] = {}
        cmdlist = self.c_commands[server.id]
        if command not in cmdlist:
            cmdlist[command] = text
            self.c_commands[server.id] = cmdlist
            dataIO.save_json(self.file_path, self.c_commands)
            await self.bot.say("Custom command successfully added.")
        else:
            await self.bot.say("This command already exists. Use editmeme to edit it.")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def editmeme(self, ctx, command: str, *, text):
        """Edits a meme

        Example:
        [p]editmeme yourcommand Text you want
        """
        server = ctx.message.server
        command = command.lower()
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if command in cmdlist:
                cmdlist[command] = text
                self.c_commands[server.id] = cmdlist
                dataIO.save_json(self.file_path, self.c_commands)
                await self.bot.say("Custom command successfully edited.")
            else:
                await self.bot.say("That command doesn't exist. Use addmeme [command] [text]")
        else:
            await self.bot.say("There are no custom memes in this server. Use addmeme [command] [text]")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def delmeme(self, ctx, command: str):
        """Deletes a meme

        Example:
        [p]delmeme yourcommand"""
        server = ctx.message.server
        command = command.lower()
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if command in cmdlist:
                cmdlist.pop(command, None)
                self.c_commands[server.id] = cmdlist
                dataIO.save_json(self.file_path, self.c_commands)
                await self.bot.say("Custom meme successfully deleted.")
            else:
                await self.bot.say("That meme doesn't exist.")
        else:
            await self.bot.say("There are no custom memes in this server. Use addmeme [command] [text]")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def setmemerole(self, ctx, rolename: str):
        """Sets the meme role

        Example:
        [p]setmemerole Regular"""

        role = get_role(ctx.message.server.roles, rolename)
        self.settings.setPrivileged(ctx.message.server.id, role.id)
        await self.bot.say("done")

    @commands.command(pass_context=True, no_pm=True)
    async def memes(self, ctx):
        """Shows custom memes list"""
        server = ctx.message.server
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if cmdlist:
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
                    await self.bot.whisper(cmds)
            else:
                await self.bot.say("There are no custom memes in this server. Use addmeme [command] [text]")
        else:
            await self.bot.say("There are no custom memes in this server. Use addmeme [command] [text]")

    async def checkCC(self, message):
        if len(message.content) < 2 or message.channel.is_private:
            return

        server = message.server
        prefix = self.get_prefix(message)

        if not prefix:
            return

        # MEME CODE
        role_id = self.settings.getPrivileged(message.server.id)
        if role_id is not None:
            role = get_role_from_id(self.bot, message.server, role_id)
            if role not in message.author.roles:
                return
        # MEME CODE

        if server.id in self.c_commands and user_allowed(message):
            cmdlist = self.c_commands[server.id]
            cmd = message.content[len(prefix):]
            if cmd in cmdlist.keys():
                cmd = cmdlist[cmd]
                cmd = self.format_cc(cmd, message)
                await self.bot.send_message(message.channel, cmd)
            elif cmd.lower() in cmdlist.keys():
                cmd = cmdlist[cmd.lower()]
                cmd = self.format_cc(cmd, message)
                await self.bot.send_message(message.channel, cmd)

    def get_prefix(self, message):
        for p in self.bot.settings.get_prefixes(message.server):
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
            "server": message.server
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
    if not dataIO.is_valid_json(f):
        print("Creating empty commands.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    n = Memes(bot)
    bot.add_listener(n.checkCC, "on_message")
    bot.add_cog(n)


class MemesSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'configs': {}
        }
        return config

    def serverConfigs(self):
        return self.bot_settings['configs']

    def getServer(self, server_id):
        configs = self.serverConfigs()
        if server_id not in configs:
            configs[server_id] = {}
        return configs[server_id]

    def getPrivileged(self, server_id):
        server = self.getServer(server_id)
        return server.get('privileged')

    def setPrivileged(self, server_id, role_id):
        server = self.getServer(server_id)
        server['privileged'] = role_id
        self.save_settings()
