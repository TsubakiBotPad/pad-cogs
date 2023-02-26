import discord
import logging
import re
from io import BytesIO
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, inline, pagify
from tsutils.cog_settings import CogSettings
from tsutils.formatting import normalize_server_name
from tsutils.user_interaction import send_cancellation_message, send_confirmation_message

logger = logging.getLogger('red.padbot-cogs.profile')


SUPPORTED_SERVERS = ["NA", "KR", "JP"]


def validate_and_clean_id(pad_id):
    pad_id = pad_id.replace('-', '').replace(' ', '').replace(',', '').replace('.', '').strip()
    if re.match(r'^\d{9}$', pad_id):
        return pad_id
    else:
        return None


def format_name_line(server, pad_name, pad_id):
    group = compute_old_group(pad_id)
    return "[{}]: '{}' : {} (Group {})".format(server, pad_name, format_id(pad_id), group)


def format_id(pad_id):
    return pad_id[0:3] + "," + pad_id[3:6] + "," + pad_id[6:9]


def compute_old_group(str_id):
    old_id_digit = str(str_id)[2]
    return chr(ord('A') + (int(old_id_digit) % 5))


class Profile(commands.Cog):
    """PAD Profile Cog"""
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = ProfileSettings("profile")

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        udata = self.settings.getUserData(user_id)

        data = "Stored data for user with ID {}:\n".format(user_id)
        if udata['servers']:
            data += " - You have a profile on the following server(s): {}.\n".format(', '.join(udata['servers']))
        if udata['default_server']:
            data += " - Your default server is {}.\n".format(udata['default_server'])

        if not any(udata.values()):
            data = "No data is stored for user with ID {}.\n".format(user_id)

        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data."""

        if requester not in ("discord_deleted_user", "owner"):
            self.settings.clearUserData(user_id)
        else:
            self.settings.clearUserDataFull(user_id)

    @commands.command()
    async def idme(self, ctx, server=None):
        """Displays your profile to the current channel

        If you do not provide a server, your default is used
        """
        profile_msg = await self.get_id_msg(ctx, ctx.author, server, False)
        if profile_msg is None:
            return

        await ctx.send(profile_msg)

    @commands.command()
    async def idto(self, ctx, user: discord.User, server=None):
        """Whispers your profile to specified user

        If you do not provide a server, your default is used
        """
        profile_msg = await self.get_id_msg(ctx, ctx.author, server)
        if profile_msg is None:
            return

        warning = "{} asked me to send you this message. Report any harassment to the mods.".format(
            ctx.author.name)
        msg = warning + "\n" + profile_msg
        await ctx.send(user, msg)
        await send_confirmation_message(ctx, "Sent your profile to " + user.name)

    @commands.command()
    async def idfor(self, ctx, user: discord.User, server=None):
        """Displays the profile of the specified user

        If you do not provide a server, your default is used.
        """
        profile_msg = await self.get_id_msg(ctx, user, server)
        if profile_msg is None:
            return

        await ctx.author.send(profile_msg)

    async def get_server(self, ctx, user_id, server=None):
        if server is None:
            server = self.settings.getDefaultServer(user_id)
        server = normalize_server_name(server)
        if server not in SUPPORTED_SERVERS:
            await send_cancellation_message(ctx, 'Unsupported server: ' + server)
            return
        return server

    async def get_id_msg(self, ctx, user, server=None, for_other=True):
        server = await self.get_server(ctx, user.id, server)
        if server is None:
            return

        pad_id = str(self.settings.getId(user.id, server))
        pad_name = self.settings.getName(user.id, server)
        profile_text = self.settings.getProfileText(user.id, server)

        line1 = "Info for " + user.name
        line2 = format_name_line(server, pad_name, pad_id)
        line3 = profile_text

        msg = line1 + "\n" + box(line2 + "\n" + line3)
        return msg

    @commands.group()
    async def profile(self, ctx):
        """Manage profile storage"""

    @profile.command()
    async def server(self, ctx, server):
        """Set your default server to one of [NA, EU, JP, KR]

        This server is used to default the idme command if you don't provide a server.
        """
        server = normalize_server_name(server)
        if server not in SUPPORTED_SERVERS:
            await send_cancellation_message(ctx, 'Unsupported server: ' + server)
            return

        self.settings.setDefaultServer(ctx.author.id, server)
        await send_confirmation_message(ctx, 'Set your default server to: ' + server)

    @profile.command(name="id")
    async def _id(self, ctx, server, *, pad_id):
        """Sets your ID for a server

        ID must be 9 digits, can be space/comma/dash delimited.
        """
        server = await self.get_server(ctx, ctx.author.id, server)
        if server is None:
            return None

        clean_id = validate_and_clean_id(pad_id)
        if clean_id is None:
            await send_cancellation_message(ctx, 'Your ID looks invalid, expected a 9 digit code, got: {}'.format(id))
            return

        self.settings.setId(ctx.author.id, server, clean_id)
        await send_confirmation_message(ctx, 'Set your id for {} to: {}'.format(server, format_id(clean_id)))

    @profile.command()
    async def name(self, ctx, server, *name):
        """Sets your in game name for a server"""
        server = await self.get_server(ctx, ctx, server)
        if server is None:
            return None

        name = " ".join(name)
        self.settings.setName(ctx.author.id, server, name)
        await send_confirmation_message(ctx, 'Set your name for {} to: {}'.format(server, name))

    @profile.command()
    async def text(self, ctx, server, *text):
        """Sets your profile text for the server.

        This info is used by the idme command and search.
        """
        server = await self.get_server(ctx, ctx.author.id, server)
        if server is None:
            return None

        text = " ".join(text).strip()

        if text == '':
            await send_cancellation_message(ctx, 'Profile text required')
            return

        self.settings.setProfileText(ctx.author.id, server, text)
        await send_confirmation_message(ctx, 'Set your profile for ' + server + ' to:\n' + text)

    @profile.command()
    async def clear(self, ctx, server=None):
        """Deletes your saved profile for a server

        If no server is provided then all profiles are deleted.
        """
        user_id = ctx.author.id
        if server is None:
            self.settings.clearProfile(user_id)
            await send_confirmation_message(ctx, 'Cleared your profile for all servers')
        else:
            server = normalize_server_name(server)
            self.settings.clearProfile(user_id, server)
            await send_confirmation_message(ctx, 'Cleared your profile for ' + server)

    @profile.command()
    async def search(self, ctx, server, *search_text):
        """profile search <server> <search text>

        Scans all profiles for the search text and PMs the results.
        """
        server = await self.get_server(ctx, ctx.author.id, server)
        if server is None:
            return None

        search_text = " ".join(search_text).strip().lower()
        if search_text == '':
            await send_cancellation_message(ctx, 'Search text required')
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
        await ctx.send(msg)

        if len(matching_profiles) == 0:
            return

        msg = 'Displaying {} matches for server {}:\n'.format(len(matching_profiles), server)
        for p in matching_profiles:
            pad_id = format_id(p['id'])
            pad_name = p.get('name', 'unknown')
            profile_text = p['text'].replace('`', '')

            line1 = "'{}' : {}".format(pad_name, pad_id)
            line2 = profile_text
            msg = msg + line1 + "\n" + line2 + "\n\n"

        await self.page_output(ctx, msg)

    async def page_output(self, ctx, msg):
        msg = msg.strip()
        msg = pagify(msg, ["\n"], shorten_by=20)
        for page in msg:
            try:
                await ctx.author.send(box(page))
            except Exception as e:
                logger.exception("page output failed " + str(e))


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

    def setId(self, user, server, pad_id):
        self.getProfile(user, server)['id'] = int(pad_id)
        self.save_settings()

    def getId(self, user, server):
        return self.getProfile(user, server).get('id', 000000000)

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

    # GDPR Compliance Functions
    def getUserData(self, user_id):
        o = {
            'servers': [],
            'default_server': '',
        }

        if user_id in self.bot_settings['default_servers']:
            o['default_server'] = self.bot_settings['default_servers'][user_id]
        if user_id in self.bot_settings['user_profiles']:
            o['servers'] = list(self.bot_settings['user_profiles'][user_id])
        return o

    def clearUserData(self, user_id):
        if user_id in self.bot_settings['default_servers']:
            del self.bot_settings['default_servers'][user_id]
        if user_id in self.bot_settings['user_profiles']:
            del self.bot_settings['user_profiles'][user_id]
        self.save_settings()

    def clearUserDataFull(self, user_id):
        self.clearUserData(user_id)
