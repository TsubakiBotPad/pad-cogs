import discord
from __main__ import send_cmd_help
from discord.ext import commands

from .rpadutils import *
from .utils import checks


class FancySay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def fancysay(self, context):
        """Make the bot say fancy things (via embeds)."""
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @fancysay.command(pass_context=True, no_pm=True)
    async def pingrole(self, ctx, role: discord.Role, *, text):
        """^fancysay pingrole rolename this is the text to ping

        1) Converts a role to mentionable
        2) Posts the message + ping in the current channel
        3) Sets the role to unmentionable
        4) Deletes the input message

        The role must be unmentionable before this command for safety.
        """
        if role.mentionable:
            await self.bot.say(inline('Error: role is already mentionable'))
            return

        try:
            await self.bot.edit_role(ctx.message.server, role, mentionable=True)
        except Exception as ex:
            await self.bot.say(inline('Error: failed to set role mentionable'))
            return

        await self.bot.delete_message(ctx.message)
        await asyncio.sleep(1)
        await self.bot.say('From {}:\n{}\n{}'.format(ctx.message.author.mention, role.mention, text))

        try:
            await self.bot.edit_role(ctx.message.server, role, mentionable=False)
        except Exception as ex:
            await self.bot.say(inline('Error: failed to set role unmentionable'))
            return

    @fancysay.command(pass_context=True, no_pm=True)
    async def emoji(self, ctx, *, text):
        """Speak the provided text as emojis, deleting the original request"""
        await self.bot.delete_message(ctx.message)
        new_msg = ""
        for char in text:
            if char.isalpha():
                new_msg += char_to_emoji(char) + ' '
            elif char == ' ':
                new_msg += '  '
            elif char.isspace():
                new_msg += char

        if len(new_msg):
            await self.bot.say(new_msg)

    @fancysay.command(pass_context=True, no_pm=True)
    async def title_description_image_footer(self, ctx, title, description, image, footer):
        """[title] [description] [image_url] [footer_text]

        You must specify a title. You can omit any of description, image, or footer.
        To omit an item use empty quotes. For the text fields, wrap your text in quotes.
        The bot will automatically delete your 'say' command if it can

        e.g. say with all fields:
        fancysay title_description_image_footer "My title text" "Description text" "xyz.com/image.png" "source: xyz.com"

        e.g. say with only title and image:
        fancysay title_descirption_image_footer "My title" "" "xyz.com/image.png" ""
        """

        embed = discord.Embed()
        if len(title):
            embed.title = title
        if len(description):
            embed.description = description
        if len(image):
            embed.set_image(url=image)
        if len(footer):
            embed.set_footer(text=footer)

        try:
            await self.bot.say(embed=embed)
            await self.bot.delete_message(ctx.message)
        except Exception as error:
            print("failed to fancysay", error)


def setup(bot):
    n = FancySay(bot)
    bot.add_cog(n)
