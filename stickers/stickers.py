import re
from collections import defaultdict

import discord
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify

from rpadutils import CogSettings

STICKER_COG = None


async def is_sticker_admin_check(ctx):
    return STICKER_COG.settings.check_admin(ctx.author.id) or await ctx.bot.is_owner(ctx.author)


def is_sticker_admin():
    return commands.check(is_sticker_admin_check)


class Stickers(commands.Cog):
    """Sticker commands."""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = StickersSettings("stickers")

        global STICKER_COG
        STICKER_COG = self

    @commands.group()
    @is_sticker_admin()
    async def sticker(self, context):
        """Global stickers."""

    @sticker.command()
    @is_sticker_admin()
    async def add(self, ctx, command: str, *, text):
        """Adds a sticker

        Example:
        !stickers add "whale happy" link_to_happy_whale
        """
        command = command.lower()
        if command in self.bot.all_commands.keys():
            await self.bot.say("That is already a standard command.")
            return

        self.settings.update_sticker(command, text)
        await ctx.send("Sticker successfully added.")

    @sticker.command()
    @is_sticker_admin()
    async def delete(self, ctx, command: str):
        """Deletes a sticker

        Example:
        !stickers delete "whale happy" """
        command = command.lower()
        if command in self.settings.get_stickers():
            self.settings.rm_sticker(command)
            await ctx.send("Sticker successfully deleted.")
        else:
            await ctx.send("Sticker doesn't exist.")

    @commands.command()
    async def stickers(self, ctx):
        """Shows all stickers"""
        if not self.settings.get_stickers():
            await ctx.send("There are no stickers yet")
            return

        stickers = list(self.settings.get_stickers())

        prefixes_list = defaultdict(list)
        other_list = list()

        for c in stickers:
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

        for prefix in sorted(prefixes_list):
            msg += " {}{} [...]\n  ".format(ctx.prefix, prefix)

            for suffix in sorted(prefixes_list[prefix]):
                msg += " {}".format(suffix)
            msg += "\n\n"

        for page in pagify(msg):
            await msg.author.send(box(page))

    @sticker.command()
    @checks.is_owner()
    async def addadmin(self, ctx, user: discord.Member):
        """Adds a user to the stickers admin"""
        self.settings.add_admin(user.id)
        await ctx.send("done")

    @sticker.command(pass_context=True)
    @checks.is_owner()
    async def rmadmin(self, ctx, user: discord.Member):
        """Removes a user from the stickers admin"""
        self.settings.rm_admin(user.id)
        await ctx.send("done")

    @commands.Cog.listener("on_message")
    async def check_for_sticker_request(self, message):
        if len(message.content) < 2:
            return

        prefix = (await self.bot.get_prefix(message))[0]

        cmdlist = self.settings.get_stickers()
        image_url = None
        cmd = message.content[len(prefix):]
        if cmd in cmdlist.keys():
            image_url = cmdlist[cmd]
        elif cmd.lower() in cmdlist.keys():
            image_url = cmdlist[cmd.lower()]

        if image_url:
            footer_text = message.content + ' posted by ' + message.author.name
            embed = discord.Embed().set_image(url=image_url).set_footer(text=footer_text)
            await message.channel.send(embed=embed)
            await message.delete()


class StickersSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'admins': [],
            'c_commands': {}
        }
        return config

    def admins(self):
        return self.bot_settings['admins']

    def check_admin(self, user_id):
        admins = self.admins()
        return user_id in admins

    def add_admin(self, user_id):
        admins = self.admins()
        if user_id not in admins:
            admins.append(user_id)
            self.save_settings()

    def rm_admin(self, user_id):
        admins = self.admins()
        if user_id in admins:
            admins.remove(user_id)
            self.save_settings()

    def get_stickers(self):
        return self.bot_settings['c_commands']

    def update_sticker(self, key, value):
        self.bot_settings['c_commands'][key] = value
        self.save_settings()

    def rm_sticker(self, key):
        self.bot_settings['c_commands'].pop(key, None)
        self.save_settings()
