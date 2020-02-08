from collections import defaultdict
import difflib
import os
import random
import re

import discord
from discord.ext import commands
from numpy.doc import glossary

from __main__ import user_allowed, send_cmd_help

from .rpadutils import *
from .rpadutils import CogSettings
from .utils import checks
from .utils.dataIO import dataIO


DONATE_MSG = """
To donate to cover bot hosting fees you can use one of:
  Patreon : https://www.patreon.com/miru_bot
  Venmo   : https://venmo.com/TacticalRetreat

Read the Patreon or join the Miru Support Server for more details:
  https://discord.gg/zB4QHgn

You permanently get some special perks for donating even $1.

The following users have donated. Thanks!
{donors}
"""

INSULTS_FILE = "data/donations/insults.json"
DEFAULT_INSULTS = {
    'miru_references': [
        'Are you talking to me you piece of shit?',
    ],
    'insults':  [
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


class Donations(commands.Cog):
    """Manages donations and perks."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = DonationsSettings("donations")

        insults_json = dataIO.load_json(INSULTS_FILE) if dataIO.is_valid_json(INSULTS_FILE) else {}
        self.insults_miru_reference = insults_json.get(
            'miru_references', DEFAULT_INSULTS['miru_references'])
        self.insults_list = insults_json.get('insults', DEFAULT_INSULTS['insults'])

        love_json = dataIO.load_json(LOVE_FILE) if dataIO.is_valid_json(LOVE_FILE) else {}
        self.cute_list = love_json.get('cute', DEFAULT_LOVE['cute'])
        self.sexy_list = love_json.get('sexy', DEFAULT_LOVE['sexy'])
        self.perverted_list = love_json.get('perverted', DEFAULT_LOVE['perverted'])

    @commands.command(pass_context=True)
    async def donate(self, ctx):
        """Prints information about donations."""
        donors = self.settings.donors()
        donor_names = set()
        for user in self.bot.get_all_members():
            if user.id in donors:
                donor_names.add(user.name)

        msg = DONATE_MSG.format(count=len(donors), donors=', '.join(sorted(donor_names)))
        await self.bot.say(box(msg))

    @commands.command(pass_context=True)
    async def mycommand(self, ctx, command: str, *, text: str):
        """Sets your custom command (donor only)."""
        user_id = ctx.message.author.id
        text = clean_global_mentions(text)
        if user_id not in self.settings.donors():
            await self.bot.say(inline('Only donors can set a personal command'))
            return

        self.settings.addCustomCommand(user_id, command, text)
        await self.bot.say(inline('I set up your command: ' + command))

    @commands.command(pass_context=True)
    async def myembed(self, ctx, command: str, title: str, url: str, footer: str):
        """Sets your custom embed command (donor only).

        This lets you create a fancier image message. For example you can set up
        a simple inline image without a link using:
        ^myembed lewd "" "http://i0.kym-cdn.com/photos/images/original/000/731/885/751.jpg" ""

        Want a title on that image? Fill in the first argument:
        ^myembed lewd "L-lewd!" "<snip, see above>" ""

        Want a footer? Fill in the last argument:
        ^myembed lewd "L-lewd!" "<snip, see above>" "source: some managa i read"
        """
        user_id = ctx.message.author.id
        if user_id not in self.settings.donors():
            await self.bot.say(inline('Only donors can set a personal command'))
            return

        self.settings.addCustomEmbed(user_id, command, title, url, footer)
        await self.bot.say(inline('I set up your embed: ' + command))

    @commands.command(pass_context=True)
    async def spankme(self, ctx):
        """You are trash (donor only)."""
        user_id = ctx.message.author.id
        if user_id not in self.settings.donors():
            await self.bot.say(inline('Donor-only command'))
            return

        await self.bot.say(ctx.message.author.mention + ' ' + random.choice(self.insults_list))

    @commands.command(pass_context=True)
    async def insultme(self, ctx):
        """You are consistently trash (donor only)."""
        user_id = ctx.message.author.id
        if user_id not in self.settings.donors():
            await self.bot.say(inline('Donor-only command'))
            return

        self.settings.addInsultsEnabled(user_id)
        await self.bot.say(ctx.message.author.mention + ' ' 'Oh, I will.\n' + random.choice(self.insults_list))

    @commands.command(pass_context=True, hidden=True)
    async def insultripper(self, ctx):
        """Fuck ripper."""
        ripper_id = '123529484476350467'
        ripper = ctx.message.server.get_member(ripper_id)
        insult = random.choice(self.insults_list)
        if ripper:
            await self.bot.say(ripper.mention + ' ' + insult)
        else:
            await self.bot.say('Ripper is not in this server but I let him know anyway')
            ripper = discord.utils.get(self.bot.get_all_members(), id=ripper_id)
            await self.bot.send_message(ripper, '{} asked me to send you this:\n{}'.format(ctx.message.author.name, insult))

    @commands.command(pass_context=True)
    async def vcinsultripper(self, ctx):
        """Fuck ripper (verbally)"""
        user_id = ctx.message.author.id
        if user_id not in self.settings.donors():
            await self.bot.say(inline('Donor-only command'))
            return

        ripper_id = '123529484476350467'
        ripper = ctx.message.server.get_member(ripper_id)

        if ripper is None:
            await self.bot.say(inline('Ripper must be in this server to use this command'))

        voice = ripper.voice
        channel = voice.voice_channel
        if channel is None:
            await self.bot.say(inline('Ripper must be in a voice channel on this server to use this command'))
            return

        insult = random.choice(self.insults_list)
        speech_cog = self.bot.get_cog('Speech')
        if not speech_cog:
            await self.bot.say(inline('Speech seems to be offline'))
            return

        await self.bot.say(ripper.mention + ' ' + insult)
        await speech_cog.speak(channel, 'Hey Ripper, ' + insult)

    @commands.command(pass_context=True)
    async def plsno(self, ctx):
        """I am merciful (donor only)."""
        user_id = ctx.message.author.id
        if user_id not in self.settings.donors():
            await self.bot.say(inline('Donor-only command'))
            return

        self.settings.rmInsultsEnabled(user_id)
        await self.bot.say('I will let you off easy this time.')

    @commands.command(pass_context=True)
    async def kissme(self, ctx):
        """You are so cute! (donor only)."""
        user_id = ctx.message.author.id
        if user_id not in self.settings.donors():
            await self.bot.say(inline('Donor-only command'))
            return

        await self.bot.say(ctx.message.author.mention + ' ' + random.choice(self.cute_list))

    @commands.command(pass_context=True)
    async def lewdme(self, ctx):
        """So nsfw. (donor only)."""
        user_id = ctx.message.author.id
        if user_id not in self.settings.donors():
            await self.bot.say(inline('Donor-only command'))
            return

        if 'nsfw' in ctx.message.channel.name.lower():
            await self.bot.say(ctx.message.author.mention + ' ' + random.choice(self.sexy_list))
        else:
            await self.bot.say(ctx.message.author.mention + ' Oooh naughty...')
            await self.bot.whisper(random.choice(self.sexy_list))

    @commands.command(pass_context=True)
    async def pervme(self, ctx):
        """Hentai!!! (donor only)."""
        user_id = ctx.message.author.id
        if user_id not in self.settings.donors():
            await self.bot.say(inline('Donor-only command'))
            return

        if 'nsfw' in ctx.message.channel.name.lower():
            await self.bot.say(ctx.message.author.mention + ' ' + random.choice(self.perverted_list))
        else:
            await self.bot.say(ctx.message.author.mention + ' Filthy hentai!')
            await self.bot.whisper(random.choice(self.perverted_list))

    @commands.group(pass_context=True)
    @checks.admin_or_permissions(manage_guild=True)
    async def donations(self, context):
        """Manage donation options."""
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @donations.command(pass_context=True)
    @checks.admin_or_permissions(manage_guild=True)
    async def togglePerks(self, ctx):
        """Enable or disable donor-specific perks for the server."""
        server_id = ctx.message.server.id
        if server_id in self.settings.disabledServers():
            self.settings.rmDisabledServer(server_id)
            await self.bot.say(inline('Donor perks enabled on this server'))
        else:
            self.settings.addDisabledServer(server_id)
            await self.bot.say(inline('Donor perks disabled on this server'))

    @donations.command(pass_context=True)
    @checks.is_owner()
    async def addDonor(self, ctx, user: discord.User):
        """Adds a a user as a donor."""
        self.settings.addDonor(user.id)
        await self.bot.say(inline('Done'))

    @donations.command(pass_context=True)
    @checks.is_owner()
    async def rmDonor(self, ctx, user: discord.User):
        """Removes a user as a donor."""
        self.settings.rmDonor(user.id)
        await self.bot.say(inline('Done'))

    @donations.command(pass_context=True)
    @checks.is_owner()
    async def addPatron(self, ctx, user: discord.User):
        """Adds a a user as a patron."""
        self.settings.addPatron(user.id)
        await self.bot.say(inline('Done'))

    @donations.command(pass_context=True)
    @checks.is_owner()
    async def rmPatron(self, ctx, user: discord.User):
        """Removes a user as a patron."""
        self.settings.rmPatron(user.id)
        await self.bot.say(inline('Done'))

    @donations.command(pass_context=True)
    @checks.is_owner()
    async def info(self, ctx):
        """Print donation related info."""
        patrons = self.settings.patrons()
        donors = self.settings.donors()
        cmds = self.settings.customCommands()
        embeds = self.settings.customEmbeds()
        disabled_servers = self.settings.disabledServers()

        id_to_name = {m.id: m.name for m in self.bot.get_all_members()}

        msg = 'Donations Info'

        msg += '\n\nPatrons:'
        for user_id in patrons:
            msg += '\n\t{} ({})'.format(id_to_name.get(user_id, 'unknown'), user_id)

        msg += '\n\nDonors:'
        for user_id in donors:
            msg += '\n\t{} ({})'.format(id_to_name.get(user_id, 'unknown'), user_id)

        msg += '\n\nDisabled servers:'
        for server_id in disabled_servers:
            server = self.bot.get_server(server_id)
            msg += '\n\t{} ({})'.format(server.name if server else 'unknown', server_id)

        msg += '\n\n{} personal commands are set'.format(len(cmds))
        msg += '\n{} personal embeds are set'.format(len(cmds))

        await self.bot.say(box(msg))

    async def checkCC(self, message):
        if len(message.content) < 2:
            return

        prefix = self.get_prefix(message)

        if not prefix:
            return

        user_id = message.author.id
        if user_id not in self.settings.donors():
            return

        if message.server and message.server.id in self.settings.disabledServers():
            return

        user_cmd = self.settings.customCommands().get(user_id)
        user_embed = self.settings.customEmbeds().get(user_id)

        cmd = message.content[len(prefix):].lower()
        if user_cmd is not None:
            if cmd == user_cmd['command']:
                await self.bot.send_message(message.channel, user_cmd['text'])
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
                await self.bot.send_message(message.channel, embed=embed)
                return

    def get_prefix(self, message):
        for p in self.bot.settings.get_prefixes(message.server):
            if message.content.startswith(p):
                return p
        return False

        return command

    async def check_insult(self, message):
        # Only opted-in people
        if message.author.id not in self.settings.insultsEnabled():
            return

        if message.server and message.server.id in self.settings.disabledServers():
            return

        content = message.clean_content
        # Ignore short messages
        if len(content) < 10:
            return

        msg = message.author.mention

        # Pretty frequently respond to direct messages
        mentions_bot = re.match(r'.*(miru|myr) bot.*', content, re.IGNORECASE) and roll(40)
        # Semi-frequently respond to miru in msg
        mentions_miru_and_roll = re.match(
            r'.*\b(miru|myr)\b.*', content, re.IGNORECASE) and roll(20)

        if mentions_bot or mentions_miru_and_roll:
            msg += ' ' + random.choice(self.insults_miru_reference)
            msg += '\n' + random.choice(self.insults_list)
            await self.bot.send_message(message.channel, msg)
            return

        # Semi-frequently respond to long messages
        long_msg_and_roll = len(content) > 200 and roll(10)
        # Occasionally respond to other messages
        short_msg_and_roll = roll(1)

        if long_msg_and_roll or short_msg_and_roll:
            msg += ' ' + random.choice(self.insults_list)
            await self.bot.send_message(message.channel, msg)
            return

        # Periodically send private messages
        if roll(7):
            msg += ' ' + random.choice(self.insults_list)
            await self.bot.send_message(message.author, msg)
            return


def setup(bot):
    n = Donations(bot)
    bot.add_listener(n.checkCC, "on_message")
    bot.add_listener(n.check_insult, "on_message")
    bot.add_cog(n)


class DonationsSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'patrons': [],
            'donors': [],
            'custom_commands': {},
            'custom_embeds': {},
            'disabled_servers': [],
            'insults_enabled': [],
        }
        return config

    def patrons(self):
        return self.bot_settings['patrons']

    def addPatron(self, user_id):
        patrons = self.patrons()
        if user_id not in patrons:
            patrons.append(user_id)
            self.save_settings()

    def rmPatron(self, user_id):
        patrons = self.patrons()
        if user_id in patrons:
            patrons.remove(user_id)
            self.save_settings()

    def donors(self):
        return self.bot_settings['donors']

    def addDonor(self, user_id):
        donors = self.donors()
        if user_id not in donors:
            donors.append(user_id)
            self.save_settings()

    def rmDonor(self, user_id):
        donors = self.donors()
        if user_id in donors:
            donors.remove(user_id)
            self.save_settings()

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
