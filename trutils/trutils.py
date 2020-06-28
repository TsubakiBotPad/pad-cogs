import asyncio
import datetime
import re
import sys

import discord
from redbot.core.bot import Red

try:
    from google.cloud import vision
except:
    print('google cloud vision not found, some features unavailable')

from redbot.core import checks, modlog
from redbot.core import commands
from redbot.core.utils.chat_formatting import inline, box, pagify

from rpadutils import CogSettings

GETMIRU_HELP = """
The new public Miru is open for invite to any server: personal, private, secret-handshake-entry-only, etc
Unlike the private Miru used by larger community servers, public Miru has lower stability requirements,
so I will install a variety of random entertainment plugins.

To invite public Miru to your server, use the following link:
https://discordapp.com/oauth2/authorize?client_id=296443771229569026&scope=bot

The following commands might come in handy:
`{0.prefix}modhelp`       - information on how to set up Miru's moderation commands
`{0.prefix}userhelp`      - a user-focused guide to Miru's commands
`{0.prefix}help`          - the full list of Miru commands

If you want to be notified of updates to Miru, suggest features, or ask for help, join the Miru Support server:
https://discord.gg/zB4QHgn
"""

USER_HELP = """
Bot user help
This command gives you an overview of the most commonly used user-focused
commands, with an emphasis on the ones unique to this bot.

Join the Miru Support Server for info, update, and bot support:
https://discord.gg/zB4QHgn

Use {0.prefix}help to get a full list of help commands. Execute any command with no
arguments to get more details on how they work.

Info commands:
{0.prefix}credits   some info about the bot
{0.prefix}donate    info on how to donate to cover hosting fees
{0.prefix}userhelp  this message
{0.prefix}modhelp   bot help specifically for mods

General:
{0.prefix}pad             lists the pad-specific global commands
{0.prefix}padfaq          lists pad-specific FAQ commands
{0.prefix}boards          lists common leader optimal board commands
{0.prefix}glossary        looks up a pad term in the glossary
{0.prefix}customcommands  lists the custom commands added by the administrators of your server
{0.prefix}memes           works the same way, but is restricted per-server to a privileged memer-only group
{0.prefix}serverinfo      stats for the current server
{0.prefix}userinfo        stats for a specific user

Monster Info:
{0.prefix}id        search for a monster by ID, full name, nickname, etc
{0.prefix}helpid    gets more info on how monster lookup works, including the nickname submission link
{0.prefix}evolist   list all the evolutions for a monster, tabbed
{0.prefix}pic       display the image for a monster

Profile:
Miru will store your personal PAD details, and provide them on request.
Use the series of commands starting with {0.prefix}profile to configure your own profile.

Use one of the following commands to retrieve data.
{0.prefix}idme            print your profile to the current channel
{0.prefix}idfor           get profile data for a specific user
{0.prefix}idto            have Miru DM your profile to a user
{0.prefix}profile search  search the list of configured (visible) profiles

Time conversion:
{0.prefix}time    get the current time in a different timezone
{0.prefix}timeto  calculate the how long until another time in another timezone

Translation:
{0.prefix}[jpen|jpus|jaen|jaus] <text>  translate text from japanese to english
"""

MOD_HELP = """
Bot Moderator Help
~~~~~~~~~~~~~~~~~~~~~~

Miru is a set of plugins inside the Red Discord bot, running on discord.py. There
are some custom ones, but a lot of them are generic to all Red Discord bots, so
things you've used elsewhere will probably also work here.

If there is a feature you're missing, let me know and I can check to see if it's
already available in some public plugin. If not, and I think it's valuable, I might
write it.

~~~~~~~~~~~~~~~~~~~~~~

Check out the {0.prefix}help command from inside your server. You'll see a wider list of
commands than normal users do.

If you've just added Miru to your server, start with the {0.prefix}modset command. You
might want to configure an Admin and a Mod role (they can be the same thing).

~~~~~~~~~~~~~~~~~~~~~~
Interesting features
~~~~~~~~~~~~~~~~~~~~~~

Self applied roles:
You can configure which roles a user can add to themself using {0.prefix}selfrole via {0.prefix}adminset

Message logs:
Discord doesn't save deleted/edited messages anywhere. Using {0.prefix}exlog you can pull
messages for a user, channel, or search for a term.

Auto Moderation:
The {0.prefix}automod2 command allows you to configure a set of rules (defined as regular expressions)
that match messages. You can then apply these rules as either a blacklist or a whitelist to
a specific channel. This allows you to force users to format their messages a specific way,
or to prevent them from saying certain things (the bot deletes violators, and notifies them
via DM).

Bad user tools:
Allows you to specify a set of roles that are applied as punishments to users, generally
restricting them from seeing or speaking in certain channels. If a punishment role is
applied to a user, the last 10 things they said (and where they said it) are recorded, and
a strike is added to their record.

You can configure a channel where Miru will log when these moderation events occur, and ping
@here asking for an explanation. She will also track when a user with a strike leaves the
server, and when they rejoin the server (as this is generally done to evade negative roles).

Custom commands:
Miru supports three types of custom commands, you can find the list of associated commands via {0.prefix}help.
* CustomCommands: Added by server mods, executable by anyone
* Memes: Added by server mods, executable only by people with a specific Role (configured by mods)
* Pad: Added by Miru PAD admins and executable by users in any server

Limiting command execution:
The '{0.prefix}p' command can be used to prevent users from executing specific commands on the server,
in specific channels, or unless they have specific roles. Read the documentation carefully.
"""


class TrUtils(commands.Cog):
    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = TrUtilsSettings("trutils")

    @commands.command()
    async def revertname(self, ctx):
        """Unsets your nickname"""
        await ctx.author.edit(nick=None)
        await ctx.send(inline('Done'))

    @commands.command()
    @checks.is_owner()
    async def loadallcogs(self, ctx):
        cogs = ['RpadUtils', 'AutoMod2', 'ChannelMod', 'Donations', 'FancySay', 'Memes',
                'PadBoard', 'Profile', 'Stickers', 'StreamCopy', 'Translate', 'VoiceRole',
                'Dadguide', 'PadGlobal', 'PadInfo']

        owner_cog = self.bot.get_cog('Core')

        for cog_name in cogs:
            cog = self.bot.get_cog(cog_name)
            if cog is None:
                await ctx.send('{} not loaded, trying to load it...'.format(cog_name))
                try:
                    await ctx.invoke(owner_cog.load, cog_name.lower())
                except Exception as e:
                    await ctx.send(box("Loading cog failed: {}: {}".format(e.__class__.__name__, str(e))))
        await ctx.send('Done!')

    @commands.command(hidden=True)
    async def traceback2(self, ctx: commands.Context, public: bool = False):
        """Sends to the owner the last command exception that has occurred

        If public (yes is specified), it will be sent to the chat instead"""
        if ctx.author.id not in [144250811315257344, 86605480876601344]:
            return

        if not public:
            destination = ctx.author
        else:
            destination = ctx.channel

        if self.bot._last_exception:
            for page in pagify(self.bot._last_exception, shorten_by=10):
                await destination.send(box(page, lang="py"))
        else:
            await ctx.send("No exception has occurred yet")

    @commands.command()
    async def getmiru(self, ctx):
        """Tells you how to get Miru into your server"""
        for page in pagify(GETMIRU_HELP.format(ctx), delims=['\n'], shorten_by=8):
            await ctx.author.send(box(page))

    @commands.command()
    async def userhelp(self, ctx):
        """Shows a summary of the useful user features"""
        for page in pagify(USER_HELP.format(ctx), delims=['\n'], shorten_by=8):
            await ctx.author.send(box(page))

    @commands.command()
    @checks.mod_or_permissions(manage_guild=True)
    async def modhelp(self, ctx):
        """Shows a summary of the useful moderator features"""
        for page in pagify(MOD_HELP.format(ctx), delims=['\n'], shorten_by=8):
            await ctx.author.send(box(page))

    @commands.command()
    async def credits(self, ctx):
        """Shows info about this bot"""
        author_repo = "https://github.com/Twentysix26"
        red_repo = author_repo + "/Red-DiscordBot"
        rpad_invite = "https://discord.gg/pad"

        about = (
            "This is an instance of [the Red Discord bot]({}), "
            "use the 'info' command for more info. "
            "The various PAD related cogs were created by tactical_retreat. "
            "Massive overhaul of the bot to Red v3 by Aradia Megido. "
            "This bot was created for the [PAD Community Server Discord]({}) but "
            "is available for other servers on request."
            "".format(red_repo, rpad_invite))

        baby_miru_url = "http://www.pixiv.net/member_illust.php?illust_id=57613867&mode=medium"
        baby_miru_author = "BOW @ Pixiv"
        cute_miru_url = "https://www.dropbox.com/s/0wlfx3g4mk8c8bg/Screenshot%202016-12-03%2018.39.37.png?dl=0"
        cute_miru_author = "Pancaaake18 on discord"
        bot_miru_url = "https://puu.sh/urTm8/c3bdf993bd.png"
        bot_miru_author = "graps on discord"
        avatar = (
            "Bot avatars supplied by:\n"
            "\t[Baby Miru]({}): {}\n"
            "\t[Cute Miru]({}): {}\n"
            "\t[Bot Miru]({}): {}"
            "".format(baby_miru_url, baby_miru_author,
                      cute_miru_url, cute_miru_author,
                      bot_miru_url, bot_miru_author))

        using = (
            "You can use `{0.prefix}help` to get a full list of commands.\n"
            "Use `{0.prefix}userhelp` to get a summary of useful user features.\n"
            "Use `{0.prefix}modhelp` to get info on moderator-only features."
        )

        embed = discord.Embed()
        embed.add_field(name="Instance owned by", value='tactical_retreat')
        embed.add_field(name="About the bot", value=about, inline=False)
        embed.add_field(name="Using the bot", value=using.format(ctx), inline=False)
        embed.add_field(name="Avatar credits", value=avatar, inline=False)
        embed.set_thumbnail(url=self.bot.user.avatar_url)

        try:
            await ctx.send(embed=embed)
        except discord.HTTPException:
            await ctx.send("I need the `Embed links` permission to send this")

    @commands.command(hidden=True)
    @checks.is_owner()
    async def supersecretdebug(self, ctx, *, code):
        """Executes superdebug and then deletes the message that triggered it.

        This is useful if you want to make the bot appear to say or do something that can't
        otherwise be easily done.
        """
        await self._superdebug(ctx, code=code)
        await ctx.message.delete()

    @commands.command(hidden=True)
    @checks.is_owner()
    async def superdebug(self, ctx, *, code):
        """Evaluates code, with a helper for asynchronous results (like ctx.send()).

        If you just want to evaluate variables, repl is a better alternative.
        """
        await self._superdebug(ctx, code=code)

    async def _superdebug(self, ctx, *, code):
        def check(m):
            if m.content.strip().lower() == "more":
                return True

        author = ctx.author
        channel = ctx.channel

        code = code.strip('` ')
        result = None

        global_vars = globals().copy()
        global_vars['bot'] = self.bot
        global_vars['ctx'] = ctx
        global_vars['message'] = ctx.message
        global_vars['author'] = ctx.author
        global_vars['channel'] = ctx.channel
        global_vars['guild'] = ctx.guild

        local_vars = locals().copy()
        local_vars['to_await'] = list()

        try:
            eval(compile(code, '<string>', 'exec'), global_vars, local_vars)
            to_await = local_vars['to_await']
        except Exception as e:
            await ctx.send(box('{}: {}'.format(type(e).__name__, str(e)),
                               lang="py"))
            return

        for result in to_await:
            if asyncio.iscoroutine(result):
                try:
                    result = await result
                except Exception as e:
                    await ctx.send(box('{}: {}'.format(type(e).__name__, str(e)),
                                       lang="py"))
            else:
                await ctx.send(result)

    @commands.command()
    @checks.is_owner()
    async def superfuckingban(self, ctx, user: discord.User, *, reason: str):
        """Really fucking bans someone.

        This will ban a user from every guild that the bot can ban them from. Use with caution.
        """
        msg = 'Ban report for {} ({}):'.format(user.name, user.id)
        for guild in self.bot.guilds:
            try:
                ban_list = await guild.bans()
                if user.id in [x.user.id for x in ban_list]:
                    msg += '\n\tUser already banned from {}'.format(guild.name)
                    continue
            except:
                msg += '\n\tNot allowed to ban in {}; nothing I can do here'.format(guild.name)
                continue

            m = guild.get_member(user.id)
            if m is None:
                try:
                    await self.bot.http.ban(user.id, guild.id, 0)
                    msg += '\n\tUser not in {}; added to hackban'.format(guild.name)
                    await modlog.create_case(bot=self.bot,
                                             guild=guild,
                                             created_at=datetime.datetime.now(),
                                             action_type="hackban",
                                             moderator=ctx.author,
                                             user=user,
                                             reason='SuperBan by bot owner: {}'.format(reason))
                except Exception as ex:
                    msg += '\n\tUser not in {}; hackban failed: {}'.format(guild.name, ex)
                continue
            try:
                await m.ban(delete_message_days=0)
                msg += '\n\tBanned from {}'.format(guild.name)
                await modlog.create_case(bot=self.bot,
                                         guild=guild,
                                         created_at=datetime.datetime.now(),
                                         action_type="ban",
                                         moderator=ctx.author,
                                         user=user,
                                         reason='SuperBan by bot owner: {}'.format(reason))
            except Exception as ex:
                msg += '\n\tFailed to ban from {} because {}'.format(guild.name, ex)

        for page in pagify(msg):
            await ctx.send(box(page))

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
        if author.avatar_url:
            e.set_author(name=description, icon_url=author.avatar_url)
        else:
            e.set_author(name=description)
        e.set_footer(text=footer)

        try:
            await feedback_channel.send(embed=e)
        except:
            await ctx.send(inline("I'm unable to deliver your message. Sorry."))
        else:
            await ctx.send(inline("Your message has been sent."
                                  " Abusing this feature will result in a blacklist."
                                  + success_message))

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def feedback(self, ctx, *, message: str):
        """Provide feedback on the bot.

        Use this command to provide public feedback on the bot.
        """
        feedback_channel = self.bot.get_channel(int(self.settings.get_feedback_channel()))
        await self._send_feedback(ctx, message, feedback_channel,
                    " Join the Miru Server to see any responses ({0.prefix}miruserver).".format(ctx))

    @commands.command()
    @commands.guild_only()
    @checks.is_owner()
    async def setfeedbackchannel(self, ctx, channel: discord.TextChannel):
        """Set the feedback destination channel."""
        self.settings.set_feedback_channel(channel.id)
        await ctx.send(inline('Done'))

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
        await ctx.send(inline('Done'))

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def mentionable(self, ctx, role: discord.Role):
        """Toggle the mentionability of a role."""
        try:
            new_mentionable = not role.mentionable
            await role.edit(mentionable=new_mentionable)
            await ctx.send(inline('Role is now {}mentionable'.format('' if new_mentionable else 'un')))
        except Exception as ex:
            await ctx.send(inline('Error: failed to alter role'))

    @commands.command()
    @checks.is_owner()
    async def freload(self, ctx, cmd, *, args=""):
        """Run a command after reloading its base cog."""
        full_cmd = "{}{} {}".format(ctx.prefix, cmd, args)
        cmd = self.bot.get_command(cmd)
        if cmd is None:
            await ctx.send("Invalid Command: {}".format(full_cmd))
            return
        await self.bot.get_cog("Core").reload(ctx, cmd.cog.__module__.split('.')[0])
        ctx.message.content = full_cmd
        await self.bot.process_commands(ctx.message)

    @commands.command()
    @checks.is_owner()
    async def pipupdate(self, ctx, module="Red-DiscordBot", updatepip=True):
        async with ctx.typing():
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", "-U", module,

                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = (bts.decode() if bts else "" for bts in await process.communicate())

        if stderr.startswith("WARNING: You are using pip version"):
            if updatepip:
                await ctx.send(stderr.split('You should consider')[0]+'\n\nUpdating pip...')
                await self.pipupdate(ctx, 'pip', False)
            stderr = ""

        if stderr:
            await ctx.author.send("Error updating:\n" + stderr)
            await ctx.send(inline("Error (sent via DM)"))
        else:
            await ctx.send(inline('Done'))

    @commands.command(hidden=True, aliases=["make_aa", "makearadia"])
    async def makeaa(self, ctx, *, task):
        await self.bot.get_user(144250811315257344).send(task)


class TrUtilsSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'servers': {},
        }
        return config

    def guilds(self):
        return self.bot_settings['servers']

    def get_guild(self, server_id):
        servers = self.guilds()
        if server_id not in servers:
            servers[server_id] = {}
        return servers[server_id]

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
