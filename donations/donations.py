import json
import random
import re

import discord
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import inline, box

from rpadutils import CogSettings, clean_global_mentions

DONATE_MSG = """
To donate to cover bot hosting fees you can use one of:
  Patreon : https://www.patreon.com/tsubaki_bot

Read the Patreon or join the Tsubaki Support Server for more details:
  https://discord.gg/tVPmeG8

You permanently get some special perks for donating even $1.

The following users have donated. Thanks!
{donors}
"""

INSULTS_FILE = "data/donations/insults.json"
DEFAULT_INSULTS = {
    'miru_references': [
        'Are you talking to me you piece of shit?',
    ],
    'insults': [
        'You are garbage.',
        'Kill yourself.',
    ]
}
LOVE_FILE = "data/donations/love.json"
DEFAULT_LOVE = {
    'cute': ['xoxo'],
    'sexy': ['{}====>'],
    'perverted': ['{}===>()'],
}


def roll(chance: int):
    return random.randrange(100) < chance

def is_patron(ctx):
    tsubaki_guild = ctx.bot.get_guild(746131494875168770)
    patron_role = tsubaki_guild.get_role(749849451769757726)
    author = tsubaki_guild.get_member(ctx.author.id)
    if author is None or patron_role not in author.roles:
        return False
    return True

def is_donor(ctx):
    tsubaki_guild = ctx.bot.get_guild(746131494875168770)
    donor_role = tsubaki_guild.get_role(749849518467580015)
    patron_role = tsubaki_guild.get_role(749849451769757726)
    author = tsubaki_guild.get_member(ctx.author.id)
    if author is None or (donor_role not in author.roles and patron_role not in author.roles):
        return False
    return True

class Donations(commands.Cog):
    """Manages donations and perks."""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = DonationsSettings("donations")

        try:
            insults_json = json.load(open(INSULTS_FILE, "r"))
        except:
            insults_json = {}
        self.insults_miru_reference = insults_json.get(
            'miru_references', DEFAULT_INSULTS['miru_references'])
        self.insults_list = insults_json.get('insults', DEFAULT_INSULTS['insults'])
        try:
            love_json = json.load(open(LOVE_FILE, "r"))
        except:
            love_json = {}
        self.cute_list = love_json.get('cute', DEFAULT_LOVE['cute'])
        self.sexy_list = love_json.get('sexy', DEFAULT_LOVE['sexy'])
        self.perverted_list = love_json.get('perverted', DEFAULT_LOVE['perverted'])

        self.tsubaki_guild = None
        self.donor_role = None
        self.patron_role = None

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        udata = self.settings.getUserData(user_id)

        data = "Stored data for user with ID {}:\n".format(user_id)
        if udata['command']:
            data += " - You have setup the command '{}'.\n".format(udata['command'])
        if udata['embed']:
            data += " - You have setup the embed '{}'.\n".format(udata['embed'])
        if udata['insult']:
            data += " - You have asked the bot to insult you occasionally.\n"

        if not any(udata.values()):
            data = "No data is stored for user with ID {}.\n".format(user_id)

        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data."""
        if requester not in ("discord_deleted_user", "owner"):
            self.settings.clearUserData(user_id)
        else:
            self.settings.clearUserDataFull(user_id)

    async def set_server_attributes(self):
        await self.bot.wait_until_ready()
        self.tsubaki_guild = self.bot.get_guild(746131494875168770)
        self.donor_role = self.tsubaki_guild.get_role(749849518467580015)
        self.patron_role = self.tsubaki_guild.get_role(749849451769757726)

    @commands.command()
    async def donate(self, ctx):
        """Prints information about donations."""
        donor_names = set()
        for user in self.tsubaki_guild.members:
            if self.donor_role in user.roles or self.patron_role in user.roles:
                donor_names.add(user.name)

        msg = DONATE_MSG.format(count=len(donor_names), donors=', '.join(sorted(donor_names)))
        await ctx.send(box(msg))

    @commands.command()
    @commands.check(is_donor)
    async def mycommand(self, ctx, command: str, *, text: str):
        """Sets your custom command."""
        text = clean_global_mentions(text)

        self.settings.addCustomCommand(ctx.author.id, command, text)
        await ctx.send(inline('I set up your command: ' + command))

    @commands.command()
    @commands.check(is_donor)
    async def myembed(self, ctx, command: str, title: str, url: str, footer: str):
        """Sets your custom embed command.

        This lets you create a fancier image message. For example you can set up
        a simple inline image without a link using:
        [p]myembed lewd "" "http://i0.kym-cdn.com/photos/images/original/000/731/885/751.jpg" ""

        Want a title on that image? Fill in the first argument:
        [p]myembed lewd "L-lewd!" "<snip, see above>" ""

        Want a footer? Fill in the last argument:
        [p]myembed lewd "L-lewd!" "<snip, see above>" "source: some managa i read"
        """

        self.settings.addCustomEmbed(ctx.author.id, command, title, url, footer)
        await ctx.send(inline('I set up your embed: ' + command))

    @commands.command()
    @commands.check(is_donor)
    async def spankme(self, ctx):
        """You are trash."""
        await ctx.send(ctx.author.mention + ' ' + random.choice(self.insults_list))

    @commands.command()
    @commands.check(is_donor)
    async def insultme(self, ctx):
        """You are consistently trash."""
        user_id = ctx.author.id

        self.settings.addInsultsEnabled(user_id)
        await ctx.send(ctx.author.mention + ' ' 'Oh, I will.\n' + random.choice(self.insults_list))

    @commands.command()
    @commands.check(is_donor)
    async def plsno(self, ctx):
        """I am merciful."""

        self.settings.rmInsultsEnabled(ctx.author.id)
        await ctx.send('I will let you off easy this time.')

    @commands.command()
    @commands.check(is_donor)
    async def kissme(self, ctx):
        """You are so cute!."""
        await ctx.send(ctx.author.mention + ' ' + random.choice(self.cute_list))

    @commands.command()
    @commands.check(is_donor)
    async def lewdme(self, ctx):
        """So nsfw.."""
        if 'nsfw' in ctx.channel.name.lower():
            await ctx.send(ctx.author.mention + ' ' + random.choice(self.sexy_list))
        else:
            await ctx.send(ctx.author.mention + ' Oooh naughty...')
            await ctx.author.send(random.choice(self.sexy_list))

    @commands.command()
    @commands.check(is_donor)
    async def pervme(self, ctx):
        """Hentai!!!."""
        if 'nsfw' in ctx.channel.name.lower():
            await ctx.send(ctx.author.mention + ' ' + random.choice(self.perverted_list))
        else:
            await ctx.send(ctx.author.mention + ' Filthy hentai!')
            await ctx.author.send(random.choice(self.perverted_list))

    @commands.group()
    @checks.admin_or_permissions(manage_guild=True)
    async def donations(self, ctx):
        """Manage donation options."""

    @donations.command()
    async def togglePerks(self, ctx):
        """Enable or disable donor-specific perks for the server."""
        server_id = ctx.guild.id
        if server_id in self.settings.disabledServers():
            self.settings.rmDisabledServer(server_id)
            await ctx.send(inline('Donor perks enabled on this server'))
        else:
            self.settings.addDisabledServer(server_id)
            await ctx.send(inline('Donor perks disabled on this server'))

    @donations.command()
    @checks.is_owner()
    async def info(self, ctx):
        """Print donation related info."""
        patrons = [user for user in self.tsubaki_guild.members if self.patron_role in user.roles]
        donors = [user for user in self.tsubaki_guild.members if self.donor_role in user.roles
                                                             and self.patron_role not in user.roles]
        cmds = self.settings.customCommands()
        embeds = self.settings.customEmbeds()
        disabled_servers = self.settings.disabledServers()

        id_to_name = {m.id: m.name for m in self.bot.get_all_members()}

        msg = 'Donations Info'

        msg += '\n\nPatrons:'
        for user in patrons:
            msg += '\n\t{} ({})'.format(user.name, user.id)

        msg += '\n\nDonors:'
        for user in donors:
            msg += '\n\t{} ({})'.format(user.name, user.id)

        msg += '\n\nDisabled servers:'
        for server_id in disabled_servers:
            server = self.bot.get_guild(int(server_id))
            msg += '\n\t{} ({})'.format(server.name if server else 'unknown', server_id)

        msg += '\n\n{} personal commands are set'.format(len(cmds))
        msg += '\n{} personal embeds are set'.format(len(cmds))

        await ctx.send(box(msg))

    @commands.Cog.listener("on_message")
    async def checkCC(self, message):
        if len(message.content) < 2:
            return

        prefix = (await self.bot.get_prefix(message))[0]

        user_id = message.author.id
        if user_id not in [user.id for user in self.tsubaki_guild.members if self.donor_role in user.roles] and \
           user_id not in [user.id for user in self.tsubaki_guild.members if self.patron_role in user.roles]:
            return

        if message.guild and message.guild.id in self.settings.disabledServers():
            return

        user_cmd = self.settings.customCommands().get(user_id)
        user_embed = self.settings.customEmbeds().get(user_id)

        cmd = message.content[len(prefix):].lower()
        if user_cmd is not None:
            if cmd == user_cmd['command']:
                await message.channel.send(user_cmd['text'])
                return
        if user_embed is not None:
            if cmd == user_embed['command']:
                embed = discord.Embed()
                title = user_embed['title']
                url = user_embed['url']
                footer = user_embed['footer']
                if len(title):
                    embed.title = title
                if len(url):
                    embed.set_image(url=url)
                if len(footer):
                    embed.set_footer(text=footer)
                await message.channel.send(embed=embed)
                return

    @commands.Cog.listener("on_message")
    async def check_insult(self, message):
        # Only opted-in people
        if message.author.id not in self.settings.insultsEnabled():
            return

        if message.guild and message.guild.id in self.settings.disabledServers():
            return

        content = message.clean_content
        # Ignore short messages
        if len(content) < 10:
            return

        msg = message.author.mention

        # Pretty frequently respond to direct messages
        mentions_bot = re.search(r'(miru|myr|tsubaki) bot', content, re.IGNORECASE) and roll(40)
        # Semi-frequently respond to miru in msg
        mentions_miru_and_roll = re.search(
            r'\b(miru|myr|tsubaki)\b', content, re.IGNORECASE) and roll(20)

        if mentions_bot or mentions_miru_and_roll:
            msg += ' ' + random.choice(self.insults_miru_reference)
            msg += '\n' + random.choice(self.insults_list)
            await message.channel.send(msg)
            return

        # Semi-frequently respond to long messages
        long_msg_and_roll = len(content) > 200 and roll(10)
        # Occasionally respond to other messages
        short_msg_and_roll = roll(1)

        if long_msg_and_roll or short_msg_and_roll:
            msg += ' ' + random.choice(self.insults_list)
            await message.channel.send(msg)
            return

        # Periodically send private messages
        if roll(7):
            msg += ' ' + random.choice(self.insults_list)
            await message.author.send(msg)
            return


class DonationsSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'custom_commands': {},
            'custom_embeds': {},
            'disabled_servers': [],
            'insults_enabled': [],
        }
        return config

    def customCommands(self):
        return self.bot_settings['custom_commands']

    def addCustomCommand(self, user_id, command, text):
        cmds = self.customCommands()
        cmds[user_id] = {
            'command': command.lower(),
            'text': text,
        }
        self.save_settings()

    def rmCustomCommand(self, user_id):
        cmds = self.customCommands()
        if user_id in cmds:
            cmds.remove(user_id)
            self.save_settings()

    def customEmbeds(self):
        return self.bot_settings['custom_embeds']

    def addCustomEmbed(self, user_id, command, title, url, footer):
        embeds = self.customEmbeds()
        embeds[user_id] = {
            'command': command.lower().strip(),
            'title': title.strip(),
            'url': url.strip(),
            'footer': footer.strip(),
        }
        self.save_settings()

    def rmCustomEmbed(self, user_id):
        embeds = self.customEmbeds()
        if user_id in embeds:
            embeds.remove(user_id)
            self.save_settings()

    def disabledServers(self):
        return self.bot_settings['disabled_servers']

    def addDisabledServer(self, server_id):
        disabled_servers = self.disabledServers()
        if server_id not in disabled_servers:
            disabled_servers.append(server_id)
            self.save_settings()

    def rmDisabledServer(self, server_id):
        disabled_servers = self.disabledServers()
        if server_id in disabled_servers:
            disabled_servers.remove(server_id)
            self.save_settings()

    def insultsEnabled(self):
        return self.bot_settings['insults_enabled']

    def addInsultsEnabled(self, user_id):
        insults_enabled = self.insultsEnabled()
        if user_id not in insults_enabled:
            insults_enabled.append(user_id)
            self.save_settings()

    def rmInsultsEnabled(self, user_id):
        insults_enabled = self.insultsEnabled()
        if user_id in insults_enabled:
            insults_enabled.remove(user_id)
            self.save_settings()

    # GDPR Compliance Functions
    def getUserData(self, user_id):
        o = {
            'command': "",
            'embed': "",
            'insult': False,
        }

        if user_id in self.bot_settings['custom_commands']:
            o['command'] = self.bot_settings['custom_commands'][user_id]["command"]
        if user_id in self.bot_settings['custom_embeds']:
            o['embed'] = self.bot_settings['custom_embeds'][user_id]["command"]
        if user_id in self.bot_settings['insults_enabled']:
            o['insult'] = True

        return o

    def clearUserData(self, user_id):
        if user_id in self.bot_settings['custom_commands']:
            del self.bot_settings['custom_commands'][user_id]
        if user_id in self.bot_settings['custom_embeds']:
            del self.bot_settings['custom_embeds'][user_id]
        if user_id in self.bot_settings['insults_enabled']:
            self.bot_settings['insults_enabled'].remove(user_id)
        self.save_settings()

    def clearUserDataFull(self, user_id):
        self.clearUserData(user_id)
