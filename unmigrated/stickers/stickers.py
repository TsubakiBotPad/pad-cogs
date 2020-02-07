import asyncio
from collections import defaultdict
import os
import re

from __main__ import user_allowed, send_cmd_help
import discord
from discord.ext import commands

from .rpadutils import *
from .rpadutils import CogSettings
from .utils import checks
from .utils.dataIO import dataIO


STICKER_COG = None


def is_sticker_admin_check(ctx):
    return STICKER_COG.settings.checkAdmin(ctx.message.author.id) or checks.is_owner_check(ctx)


def is_sticker_admin():
    return commands.check(is_sticker_admin_check)


class Stickers:
    """Sticker commands."""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/stickers/commands.json"
        self.c_commands = dataIO.load_json(self.file_path)
        self.settings = StickersSettings("stickers")

        global STICKER_COG
        STICKER_COG = self

    @commands.group(pass_context=True)
    @is_sticker_admin()
    async def sticker(self, context):
        """Global stickers."""
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @sticker.command(pass_context=True)
    @is_sticker_admin()
    async def add(self, ctx, command: str, *, text):
        """Adds a sticker

        Example:
        !stickers add "whale happy" link_to_happy_whale
        """
        command = command.lower()
        if command in self.bot.commands.keys():
            await self.bot.say("That is already a standard command.")
            return
        if not self.c_commands:
            self.c_commands = {}
        cmdlist = self.c_commands

        cmdlist[command] = text
        dataIO.save_json(self.file_path, self.c_commands)
        await self.bot.say("Sticker successfully added.")

    @sticker.command(pass_context=True)
    @is_sticker_admin()
    async def delete(self, ctx, command: str):
        """Deletes a sticker

        Example:
        !stickers delete "whale happy" """
        command = command.lower()
        cmdlist = self.c_commands
        if command in cmdlist:
            cmdlist.pop(command, None)
            dataIO.save_json(self.file_path, self.c_commands)
            await self.bot.say("Sticker successfully deleted.")
        else:
            await self.bot.say("Sticker doesn't exist.")

    @commands.command(pass_context=True)
    async def stickers(self, ctx):
        """Shows all stickers"""
        cmdlist = self.c_commands
        if not cmdlist:
            await self.bot.say("There are no stickers yet")
            return

        commands = list(cmdlist.keys())

        prefixes_list = defaultdict(list)
        other_list = list()

        for c in commands:
            m = re.match(r'^(.+)[ ](.+)$', c)
            if m:
                grp = m.group(1)
                prefixes_list[grp].append(m.group(2))
            else:
                other_list.append(c)

        msg = "Stickers:\n"
        for cmd in sorted(other_list):
            msg += " {}{}\n".format(ctx.prefix, cmd)

        msg += "\nSticker Packs:\n"

        for prefix in sorted(prefixes_list.keys()):
            msg += " {}{} [...]\n  ".format(ctx.prefix, prefix)

            for suffix in sorted(prefixes_list[prefix]):
                msg += " {}".format(suffix)
            msg += "\n\n"

        for page in pagify(msg):
            await self.bot.whisper(box(page))

    @sticker.command(pass_context=True)
    @checks.is_owner()
    async def addadmin(self, ctx, user: discord.Member):
        """Adds a user to the stickers admin"""
        self.settings.addAdmin(user.id)
        await self.bot.say("done")

    @sticker.command(pass_context=True)
    @checks.is_owner()
    async def rmadmin(self, ctx, user: discord.Member):
        """Removes a user from the stickers admin"""
        self.settings.rmAdmin(user.id)
        await self.bot.say("done")

    async def checkCC(self, message):
        if len(message.content) < 2:
            return

        prefix = self.get_prefix(message)

        if not prefix:
            return

        cmdlist = self.c_commands
        image_url = None
        cmd = message.content[len(prefix):]
        if cmd in cmdlist.keys():
            image_url = cmdlist[cmd]
        elif cmd.lower() in cmdlist.keys():
            image_url = cmdlist[cmd.lower()]

        if image_url:
            footer_text = message.content + ' posted by ' + message.author.name
            embed = discord.Embed().set_image(url=image_url).set_footer(text=footer_text)
            sticker_msg = await self.bot.send_message(message.channel, embed=embed)

            await self.bot.delete_message(message)
#             await asyncio.sleep(15)
#             await self.bot.delete_message(sticker_msg)

    def get_prefix(self, message):
        for p in self.bot.settings.get_prefixes(message.server):
            if message.content.startswith(p):
                return p
        return False


def check_folders():
    if not os.path.exists("data/stickers"):
        print("Creating data/stickers folder...")
        os.makedirs("data/stickers")


def check_files():
    f = "data/stickers/commands.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty commands.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    n = Stickers(bot)
    bot.add_listener(n.checkCC, "on_message")
    bot.add_cog(n)


class StickersSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'admins': []
        }
        return config

    def admins(self):
        return self.bot_settings['admins']

    def checkAdmin(self, user_id):
        admins = self.admins()
        return user_id in admins

    def addAdmin(self, user_id):
        admins = self.admins()
        if user_id not in admins:
            admins.append(user_id)
            self.save_settings()

    def rmAdmin(self, user_id):
        admins = self.admins()
        if user_id in admins:
            admins.remove(user_id)
            self.save_settings()
