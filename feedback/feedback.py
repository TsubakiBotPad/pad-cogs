from io import BytesIO

import discord
from redbot.core import checks, commands, Config
from redbot.core.utils.chat_formatting import inline
from tsutils.cog_settings import CogSettings


class Feedback(commands.Cog):
    """Feedback Cog"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = FeedbackSettings("feedback")
        self.config = Config.get_conf(self, identifier=73308437)
        self.config.register_global(feedback_server="")

        self.sessions = set()

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    async def _send_feedback(self, ctx, message: str, feedback_channel, success_message: str):
        if feedback_channel is None:
            raise commands.UserFeedbackCheckFailure("Feedback channel not set")

        guild = ctx.guild
        author = ctx.author
        footer = "User ID: " + str(author.id)

        if guild:
            source = "from {}".format(guild)
            footer += " | Guild ID: " + str(guild.id)
        else:
            source = "through DM"

        description = "Sent by {} {}".format(author, source)

        e = discord.Embed(description=message)
        if author.avatar.url:
            e.set_author(name=description, icon_url=ctx.author.avatar.url)
        else:
            e.set_author(name=description)
        e.set_footer(text=footer)

        try:
            await feedback_channel.send(embed=e)
        except:
            await ctx.send(inline("I'm unable to deliver your message. Sorry."))
        else:
            await ctx.send(("Your message has been sent."
                            " Thanks so much for helping to improve Tsubaki Bot!")
                           + success_message)

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def credits(self, ctx):
        """Shows info about this bot"""
        author_repo = "https://github.com/Twentysix26"
        red_repo = author_repo + "/Red-DiscordBot"
        rpad_invite = "https://discord.gg/pad"

        about = (
            "This is an instance of [the Red Discord bot]({}), "
            "use the '{}info' command for more info. "
            "The various PAD related cogs were created by Aradia Megido and tactical_retreat. "
            "This bot was created for the [PAD Community Server Discord]({}) but "
            "is available for other servers on request."
            "".format(red_repo, ctx.prefix, rpad_invite))

        avatar = (
            "Bot avatars supplied by:\n"
            "\t[Tsubaki]({}): {}").format("https://twitter.com/_violebot", "Violebot")

        using = (
            "You can use `{0.prefix}help` to get a full list of commands.\n"
            "Use `{0.prefix}userhelp` to get a summary of useful user features.\n"
            "Use `{0.prefix}modhelp` to get info on moderator-only features."
        )

        embed = discord.Embed()
        embed.add_field(name="Instance owned by", value='The Tsubaki Team')
        embed.add_field(name="About the bot", value=about, inline=False)
        embed.add_field(name="Using the bot", value=using.format(ctx), inline=False)
        embed.add_field(name="Avatar credits", value=avatar, inline=False)
        embed.set_thumbnail(url=self.bot.user.avatar.url)

        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def feedback(self, ctx, *, message: str):
        """Provide feedback on the bot.

        Use this command to provide public feedback on the bot.
        """
        feedback_channel = self.bot.get_channel(int(self.settings.get_feedback_channel()))
        await self._send_feedback(ctx, message, feedback_channel,
                                  ("\nJoin the Tsubaki Server to see any responses.\n"
                                   "{}").format(await self.config.feedback_server()))

    @commands.command()
    @commands.guild_only()
    @checks.is_owner()
    async def setfeedbackchannel(self, ctx, channel: discord.TextChannel):
        """Set the feedback destination channel."""
        self.settings.set_feedback_channel(channel.id)
        await ctx.tick()

    @commands.command(aliases=['mamafeedback', 'renifeedback'])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def blogfeedback(self, ctx, *, message: str):
        """Provide feedback on Reni's blog or translations.

        Use this command to submit feedback on https://pad.protic.site or the JP translations.
        """
        feedback_channel = self.bot.get_channel(int(self.settings.get_blog_feedback_channel()))
        await self._send_feedback(ctx, message, feedback_channel,
                                  " Join the PDX Server to see any responses ({0.prefix}pdx).".format(ctx))

    @commands.command()
    @commands.guild_only()
    @checks.is_owner()
    async def setblogfeedbackchannel(self, ctx, channel: discord.TextChannel):
        """Set the blog feedback destination channel."""
        self.settings.set_blog_feedback_channel(channel.id)
        await ctx.tick()

    @feedback.command()
    @checks.is_owner()
    @commands.cooldown(1, 0, commands.BucketType.user)
    async def setserverinvite(self, ctx, *, invite):
        """Set the blog feedback destination channel."""
        await self.config.feedback_server.set(invite)
        await ctx.tick()


class FeedbackSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'feedback_channel': None,
            'blog_feedback_channel': None,
        }
        return config

    def get_feedback_channel(self):
        return self.bot_settings.get('feedback_channel')

    def set_feedback_channel(self, channel_id: int):
        self.bot_settings['feedback_channel'] = str(channel_id)
        self.save_settings()

    def get_blog_feedback_channel(self):
        return self.bot_settings.get('blog_feedback_channel')

    def set_blog_feedback_channel(self, channel_id: int):
        self.bot_settings['blog_feedback_channel'] = str(channel_id)
        self.save_settings()
