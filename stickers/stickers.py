import re
from collections import defaultdict

from redbot.core import checks
from redbot.core import commands
from redbot.core.utils.chat_formatting import *

from rpadutils import CogSettings, safe_read_json, writeJsonFile, ensure_json_exists

STICKER_COG = None


def is_sticker_admin_check(ctx: commands.Context):
    is_owner = ctx.bot.owner_id == ctx.author.id
    is_sticker_admin = STICKER_COG.settings.checkAdmin(ctx.author.id)
    return is_sticker_admin or is_owner


def is_sticker_admin():
    return commands.check(is_sticker_admin_check)


class Stickers(commands.Cog):
    """Sticker commands."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.file_path = "data/stickers/commands.json"
        self.c_commands = safe_read_json(self.file_path)
        self.settings = StickersSettings("stickers")

        global STICKER_COG
        STICKER_COG = self

    @commands.group(pass_context=True)
    @is_sticker_admin()
    async def sticker(self, ctx: commands.Context) -> None:
        """Global stickers."""
        pass

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
        writeJsonFile(self.file_path, self.c_commands)
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
            writeJsonFile(self.file_path, self.c_commands)
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

        ctx = await self.bot.get_context(message)
        if ctx.prefix is None or ctx.valid:
            return
        prefix = ctx.prefix

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


def check_files():
    ensure_json_exists('data/stickers', 'commands.json')


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
