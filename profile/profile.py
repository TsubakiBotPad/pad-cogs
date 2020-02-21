import re

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import inline, box, pagify

from rpadutils import CogSettings


def normalizeServer(server):
    server = server.upper().strip()
    return 'NA' if server == 'US' else server


SUPPORTED_SERVERS = ["NA", "KR", "JP", "EU"]


def validateAndCleanId(id):
    id = id.replace('-', '').replace(' ', '').replace(',', '').replace('.', '').strip()
    if re.match(r'^\d{9}$', id):
        return id
    else:
        return None


def formatNameLine(server, pad_name, pad_id):
    group = computeOldGroup(pad_id)
    return "[{}]: '{}' : {} (Group {})".format(server, pad_name, formatId(pad_id), group)


def formatId(id):
    return id[0:3] + "," + id[3:6] + "," + id[6:9]


def computeOldGroup(str_id):
    old_id_digit = str_id[2]
    return chr(ord('A') + (int(old_id_digit) % 5))


class Profile(commands.Cog):
    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = ProfileSettings("profile")

    async def on_ready(self):
        """ready"""
        print("started profile")

    @commands.command(name="idme")
    async def idMe(self, ctx, server=None):
        """Prints out your profile to the current channel

        If you do not provide a server, your default is used
        """
        profile_msg = await self.getIdMsg(ctx, ctx.author, server, False)
        if profile_msg is None:
            return

        await ctx.send(profile_msg)

    @commands.command(name="idto")
    async def idTo(self, ctx, user: discord.Member, server=None):
        """Whispers your profile to specified user

        If you do not provide a server, your default is used
        """
        profile_msg = await self.getIdMsg(ctx, ctx.author, server)
        if profile_msg is None:
            return

        warning = inline("{} asked me to send you this message. Report any harassment to the mods.".format(
            ctx.author.name))
        msg = warning + "\n" + profile_msg
        await ctx.send(user, msg)
        await ctx.author.send(inline("Sent your profile to " + user.name))

    @commands.command(name="idfor")
    async def idFor(self, ctx, user: discord.Member, server=None):
        """Prints out the profile of the specified user

        If you do not provide a server, your default is used.
        """
        profile_msg = await self.getIdMsg(ctx, user, server)
        if profile_msg is None:
            return

        await ctx.author.send(profile_msg)

    async def getServer(self, ctx, user_id, server=None):
        if server is None:
            server = self.settings.getDefaultServer(user_id)
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send(inline('Unsupported server: ' + server))
            return
        return server

    async def getIdMsg(self, ctx, user, server=None, for_other=True):
        server = await self.getServer(ctx, user.id, server)
        if server is None:
            return

        pad_id = self.settings.getId(user.id, server)
        pad_name = self.settings.getName(user.id, server)
        profile_text = self.settings.getProfileText(user.id, server)

        line1 = "Info for " + user.name
        line2 = formatNameLine(server, pad_name, pad_id)
        line3 = profile_text

        msg = inline(line1) + "\n" + box(line2 + "\n" + line3)
        return msg

    @commands.group()
    async def profile(self, ctx):
        """Manage profile storage"""

    @profile.command(name="server")
    async def setServer(self, ctx, server):
        """Set your default server to one of [NA, EU, JP, KR]

        This server is used to default the idme command if you don't provide a server.
        """
        server = normalizeServer(server)
        if server not in SUPPORTED_SERVERS:
            await ctx.send(inline('Unsupported server: ' + server))
            return

        self.settings.setDefaultServer(ctx.author.id, server)
        await ctx.send(inline('Set your default server to: ' + server))

    @profile.command(name="id")
    async def setId(self, ctx, server, *id):
        """Sets your ID for a server

        ID must be 9 digits, can be space/comma/dash delimited.
        """
        server = await self.getServer(ctx, ctx.author.id, server)
        if server is None:
            return None

        id = " ".join(id)
        clean_id = validateAndCleanId(id)
        if clean_id is None:
            await ctx.send(inline('Your ID looks invalid, expected a 9 digit code, got: {}'.format(id)))
            return

        self.settings.setId(ctx.author.id, server, clean_id)
        await ctx.send(inline('Set your id for {} to: {}'.format(server, formatId(clean_id))))

    @profile.command(name="name")
    async def setName(self, ctx, server, *name):
        """Sets your in game name for a server"""
        server = await self.getServer(ctx, ctx, server)
        if server is None:
            return None

        name = " ".join(name)
        self.settings.setName(ctx.author.id, server, name)
        await ctx.send(inline('Set your name for {} to: {}'.format(server, name)))

    @profile.command(name="text")
    async def setText(self, ctx, server, *text):
        """Sets your profile text for the server.

        This info is used by the idme command and search.
        """
        server = await self.getServer(ctx, ctx.author.id, server)
        if server is None:
            return None

        text = " ".join(text).strip()

        if text == '':
            await ctx.send(inline('Profile text required'))
            return

        self.settings.setProfileText(ctx.author.id, server, text)
        await ctx.send(inline('Set your profile for ' + server + ' to:\n' + text))

    @profile.command(name="clear")
    async def clear(self, ctx, server=None):
        """Deletes your saved profile for a server

        If no server is provided then all profiles are deleted.
        """
        user_id = ctx.author.id
        if server is None:
            self.settings.clearProfile(user_id)
            await ctx.send(inline('Cleared your profile for all servers'))
        else:
            server = normalizeServer(server)
            self.settings.clearProfile(user_id, server)
            await ctx.send(inline('Cleared your profile for ' + server))

    @profile.command(name="search")
    async def search(self, ctx, server, *search_text):
        """profile search <server> <search text>

        Scans all profiles for the search text and PMs the results.
        """
        server = await self.getServer(ctx, ctx.author.id, server)
        if server is None:
            return None

        search_text = " ".join(search_text).strip().lower()
        if search_text == '':
            await ctx.send(inline('Search text required'))
            return

        # Get all profiles for server
        profiles = [p[server] for p in self.settings.profiles().values() if server in p]
        # Eliminate profiles without an ID set
        profiles = filter(lambda p: 'id' in p, profiles)
        profiles = list(profiles)

        # Match the profiles against the search text
        matching_profiles = filter(lambda p: search_text in p.get('text', '').lower(), profiles)
        matching_profiles = list(matching_profiles)

        template = 'Found {}/{} matching profiles in {} for : {}'
        msg = template.format(len(matching_profiles), len(profiles), server, search_text)
        await ctx.send(inline(msg))

        if len(matching_profiles) == 0:
            return

        msg = 'Displaying {} matches for server {}:\n'.format(len(matching_profiles), server)
        for p in matching_profiles:
            pad_id = formatId(p['id'])
            pad_name = p.get('name', 'unknown')
            profile_text = p['text'].replace('`', '')

            line1 = "'{}' : {}".format(pad_name, pad_id)
            line2 = profile_text
            msg = msg + line1 + "\n" + line2 + "\n\n"

        await self.pageOutput(ctx, msg)

    async def pageOutput(self, ctx, msg):
        msg = msg.strip()
        msg = pagify(msg, ["\n"], shorten_by=20)
        for page in msg:
            try:
                await ctx.author.send(box(page))
            except Exception as e:
                print("page output failed " + str(e))
                print("tried to print: " + page)


class ProfileSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'default_servers': {},
            'user_profiles': {},
        }
        return config

    def profiles(self):
        return self.bot_settings['user_profiles']

    def default_server(self):
        return self.bot_settings['default_servers']

    def setDefaultServer(self, user, server):
        self.default_server()[user] = server
        self.save_settings()

    def getDefaultServer(self, user):
        return self.default_server().get(user, 'NA')

    def getProfile(self, user, server):
        profiles = self.profiles()
        if user not in profiles:
            profiles[user] = {}
        profile = profiles[user]
        if server not in profile:
            profile[server] = {}
        return profile[server]

    def setId(self, user, server, id):
        self.getProfile(user, server)['id'] = id
        self.save_settings()

    def getId(self, user, server):
        return self.getProfile(user, server).get('id', '000000000')

    def setName(self, user, server, name):
        self.getProfile(user, server)['name'] = name
        self.save_settings()

    def getName(self, user, server):
        return self.getProfile(user, server).get('name', 'name not set')

    def setProfileText(self, user, server, text):
        self.getProfile(user, server)['text'] = text
        self.save_settings()

    def getProfileText(self, user, server):
        return self.getProfile(user, server).get('text', 'profile text not set')

    def clearProfile(self, user, server=None):
        if server is None:
            self.profiles().pop(user, None)
        else:
            self.getProfile(user, server).clear()
        self.save_settings()
