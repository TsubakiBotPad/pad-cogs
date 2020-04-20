"""
Utilities for managing misbehaving users and facilitating administrator
communication about role changes.
"""

from collections import defaultdict
from collections import deque

import discord
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, inline, pagify

from rpadutils import CogSettings, get_role, get_role_from_id

LOGS_PER_USER = 10


class BadUser(commands.Cog):
    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.settings = BadUserSettings("baduser")
        self.logs = defaultdict(lambda: deque(maxlen=LOGS_PER_USER))

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def baduser(self, ctx):
        """BadUser tools.

        The scope of this module has expanded a bit. It now covers both 'positive' and 'negative'
        roles. The goal is to assist coordination across moderators.

        When a user receives a negative role, a strike is automatically recorded for them. This
        captures their recent message history.

        You can specify a moderation channel for announcements. An announcement occurs on the
        following events:
        * User gains or loses a negative/positive role (includes a ping to @here)
        * User with a strike leaves the server
        * User with a strike joins the server (includes a ping to @here)

        Besides the automatic tracking, you can manually add strikes, print them, and clear them.
        """

    @baduser.command(name="addnegativerole")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addNegativeRole(self, ctx, *, role):
        """Designate a role as a 'punishment' role."""
        role = get_role(ctx.guild.roles, role)
        self.settings.addPunishmentRole(ctx.guild.id, role.id)
        await ctx.send(inline('Added punishment role "' + role.name + '"'))

    @baduser.command(name="rmnegativerole")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmNegativeRole(self, ctx, *, role):
        """Cancels a role from 'punishment' status."""
        role = get_role(ctx.guild.roles, role)
        self.settings.rmPunishmentRole(ctx.guild.id, role.id)
        await ctx.send(inline('Removed punishment role "' + role.name + '"'))

    @baduser.command(name="addpositiverole")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addPositiveRole(self, ctx, *, role):
        """Designate a role as a 'benefit' role."""
        role = get_role(ctx.guild.roles, role)
        self.settings.addPositiveRole(ctx.guild.id, role.id)
        await ctx.send(inline('Added positive role "' + role.name + '"'))

    @baduser.command(name="rmpositiverole")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmPositiveRole(self, ctx, *, role):
        """Cancels a role from 'benefit' status."""
        role = get_role(ctx.guild.roles, role)
        self.settings.rmPositiveRole(ctx.guild.id, role.id)
        await ctx.send(inline('Removed positive role "' + role.name + '"'))

    @baduser.command(name="addneutralrole")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addNeutralRole(self, ctx, *, role):
        """Designate a role as a notable but not ping-worthy role."""
        role = get_role(ctx.guild.roles, role)
        self.settings.addNeutralRole(ctx.guild.id, role.id)
        await ctx.send(inline('Added neutral role "' + role.name + '"'))

    @baduser.command(name="rmneutralrole")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def rmNeutralRole(self, ctx, *, role):
        """Cancels a role from notable but not ping-worthy status."""
        role = get_role(ctx.guild.roles, role)
        self.settings.rmNeutralRole(ctx.guild.id, role.id)
        await ctx.send(inline('Removed neutral role "' + role.name + '"'))

    @baduser.command(name="setchannel")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def setChannel(self, ctx, channel: discord.TextChannel):
        """Set the channel for moderation announcements."""
        self.settings.updateChannel(ctx.guild.id, channel.id)
        await ctx.send(inline('Set the announcement channel'))

    @baduser.command(name="clearchannel")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def clearChannel(self, ctx):
        """Clear the channel for moderation announcements."""
        self.settings.updateChannel(ctx.guild.id, None)
        await ctx.send(inline('Cleared the announcement channel'))

    @baduser.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def togglestrikeprivacy(self, ctx):
        """Change strike existance policy."""
        server = ctx.guild
        self.settings.setStrikesPrivate(server.id, not self.settings.getStrikesPrivate(server.id))
        output = '\nStrike existance is now ' + \
                 'private' if self.settings.getStrikesPrivate(server.id) else 'public'
        await ctx.send(inline(output))

    @baduser.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def config(self, ctx):
        """Print the baduser configuration."""
        server = ctx.guild
        output = 'Punishment roles:\n'
        for role_id in self.settings.getPunishmentRoles(server.id):
            try:
                role = get_role_from_id(self.bot, server, role_id)
                output += '\t' + role.name + '\n'
            except Exception as e:
                pass  # Role was deleted

        output += '\nPositive roles:\n'
        for role_id in self.settings.getPositiveRoles(server.id):
            try:
                role = get_role_from_id(self.bot, server, role_id)
                output += '\t' + role.name + '\n'
            except Exception as e:
                pass  # Role was deleted

        output += '\nNeutral roles:\n'
        for role_id in self.settings.getNeutralRoles(server.id):
            try:
                role = get_role_from_id(self.bot, server, role_id)
                output += '\t' + role.name + '\n'
            except Exception as e:
                pass  # Role was deleted

        output += '\nStrike contents are private'
        output += '\nStrike existence is ' + \
                  ('private' if self.settings.getStrikesPrivate(server.id) else 'public')

        await ctx.send(box(output))

    @baduser.command(name="strikes")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def strikes(self, ctx, user: discord.User):
        """Print the strike count for a user."""
        strikes = self.settings.countUserStrikes(ctx.guild.id, user.id)
        await ctx.send(box('User {} has {} strikes'.format(user.name, strikes)))

    @baduser.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def addstrike(self, ctx, user: discord.User, *, strike_text: str):
        """Manually add a strike to a user."""
        timestamp = str(ctx.message.created_at)[:-7]
        msg = 'Manually added by {} ({}): {}'.format(
            ctx.author.name, timestamp, strike_text)
        server_id = ctx.guild.id
        self.settings.updateBadUser(server_id, user.id, msg)
        strikes = self.settings.countUserStrikes(server_id, user.id)
        await ctx.send(box('Done. User {} now has {} strikes'.format(user.name, strikes)))

    @baduser.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def clearstrikes(self, ctx, user: discord.User):
        """Clear all strikes for a user."""
        self.settings.clearUserStrikes(ctx.guild.id, user.id)
        await ctx.send(box('Cleared strikes for {}'.format(user.name)))

    @baduser.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def printstrikes(self, ctx, user: discord.User):
        """Print all strikes for a user."""
        strikes = self.settings.getUserStrikes(ctx.guild.id, user.id)
        if not strikes:
            await ctx.send(box('No strikes for {}'.format(user.name)))
            return

        for idx, strike in enumerate(strikes):
            await ctx.send(inline('Strike {} of {}:'.format(idx + 1, len(strikes))))
            await ctx.send(box(strike))

    @baduser.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def deletestrike(self, ctx, user: discord.User, strike_num: int):
        """Delete a specific strike for a user."""
        strikes = self.settings.getUserStrikes(ctx.guild.id, user.id)
        if not strikes or len(strikes) < strike_num:
            await ctx.send(box('Strike not found for {}'.format(user.name)))
            return

        strike = strikes[strike_num - 1]
        strikes.remove(strike)
        self.settings.setUserStrikes(ctx.guild.id, user.id, strikes)
        await ctx.send(inline('Removed strike {}. User has {} remaining.'.format(strike_num, len(strikes))))
        await ctx.send(box(strike))

    @baduser.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def report(self, ctx):
        """Displays a report of information on bad users for the server."""
        cur_server = ctx.guild
        user_id_to_ban_server = defaultdict(list)
        user_id_to_baduser_server = defaultdict(list)
        error_messages = list()
        for server in self.bot.guilds:
            if server.id == cur_server.id:
                continue

            if self.settings.getStrikesPrivate(server.id):
                error_messages.append("Server '{}' set its strikes private".format(server.name))
                continue

            try:
                ban_list = await self.bot.get_bans(server)
            except:
                ban_list = list()
                error_messages.append("Server '{}' refused access to ban list".format(server.name))

            for user in ban_list:
                user_id_to_ban_server[user.id].append(server.id)

            baduser_list = self.settings.getBadUsers(server.id)
            for user_id in baduser_list:
                user_id_to_baduser_server[user_id].append(server.id)

        bad_users = self.settings.getBadUsers(cur_server.id)

        baduser_entries = list()
        otheruser_entries = list()

        for member in cur_server.members:
            local_strikes = self.settings.getUserStrikes(cur_server.id, member.id)
            other_baduser_servers = user_id_to_baduser_server[member.id]
            other_banned_servers = user_id_to_ban_server[member.id]

            if not len(local_strikes) and not len(other_baduser_servers) and not len(other_banned_servers):
                continue

            tmp_msg = "{} ({})".format(member.name, member.id)
            if other_baduser_servers:
                tmp_msg += "\n\tbad user in {} other servers".format(len(other_baduser_servers))
            if other_banned_servers:
                tmp_msg += "\n\tbanned from {} other servers".format(len(other_banned_servers))

            if len(local_strikes):
                tmp_msg += "\n\t{} strikes in this server".format(len(local_strikes))
                for strike in local_strikes:
                    tmp_msg += "\n\t\t{}".format(strike.splitlines()[0])
                baduser_entries.append(tmp_msg)
            else:
                otheruser_entries.append(tmp_msg)

        other_server_count = len(self.bot.guilds) - 1
        other_ban_count = len([x for x, l in user_id_to_ban_server.items() if len(l)])
        other_baduser_count = len([x for x, l in user_id_to_baduser_server.items() if len(l)])
        msg = "Across {} other servers, {} users are banned and {} have baduser entries".format(
            other_server_count, other_ban_count, other_baduser_count)

        msg += "\n\n{} baduser entries for this server".format(len(baduser_entries))
        msg += "\n" + "\n".join(baduser_entries)
        msg += "\n\n{} entries for users with no record in this server".format(
            len(otheruser_entries))
        msg += "\n" + "\n".join(otheruser_entries)

        if error_messages:
            msg += "\n\nSome errors occurred:"
            msg += "\n" + "\n".join(error_messages)

        for page in pagify(msg):
            await ctx.send(box(page))

    @baduser.command()
    @checks.is_owner()
    async def addban(self, ctx, user_id: int, *, reason: str):
        self.settings.addBannedUser(user_id, reason)
        await ctx.send(inline('Done'))

    @baduser.command()
    @checks.is_owner()
    async def rmban(self, ctx, user_id: int):
        user_id = str(user_id)
        self.settings.rmBannedUser(user_id)
        await ctx.send(inline('Done'))

    @baduser.command()
    @commands.guild_only()
    @checks.is_owner()
    async def globalcheckbanlist(self, ctx):
        bans = await self._load_banned_users()
        msg = 'Checking for banned users in {} guilds'.format(len(self.bot.guilds))
        for cur_server in self.bot.guilds:
            msg += await self._check_ban_list(cur_server)

        for page in pagify(msg):
            await ctx.send(box(page))

    @baduser.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def checkbanlist(self, ctx):
        msg = 'Checking for banned users'
        msg += await self._check_ban_list(ctx.guild)
        await ctx.send(box(msg))

    async def _check_ban_list(self, server: discord.Guild):
        # external_ban_list is [user_id]
        # local_ban_list is {user.id : reason}
        external_bans = await self._load_banned_users()
        local_bans = self.settings.bannedUsers()
        msg = '\n\tChecking {}'.format(server.name)
        for member in server.members:
            if member.id in external_bans:
                msg += '\n\t\tExternal banned user: {} ({})'.format(member.name, member.id)
            if member.id in local_bans:
                msg += '\n\t\tLocal banned user: {} ({}) for: {}'.format(
                    member.name, member.id, local_bans[member.id])
        return msg

    @commands.Cog.listener('on_message')
    async def mod_message(self, message):
        if message.author.id == self.bot.user.id or isinstance(message.channel, discord.abc.PrivateChannel):
            return

        author = message.author
        content = message.clean_content
        channel = message.channel
        timestamp = str(message.created_at)[:-7]
        log_msg = '[{}] {} ({}): {}/{}'.format(timestamp, author.name,
                                               author.id, channel.name, content)
        self.logs[author.id].append(log_msg)

    @commands.Cog.listener('on_member_ban')
    async def mod_ban(self, guild, user):
        await self.recordBadUser(user, 'BANNED')

    @commands.Cog.listener('on_member_remove')
    async def mod_user_left(self, member):
        strikes = self.settings.countUserStrikes(member.guild.id, member.id)
        if strikes:
            msg = 'FYI: A user with {} strikes just left the server: {}'.format(
                strikes, member.name)
            update_channel = self.settings.getChannel(member.guild.id)
            if update_channel is not None:
                channel_obj = member.guild.get_channel(update_channel)
                await channel_obj.send(msg)

    @commands.Cog.listener('on_member_join')
    async def mod_user_join(self, member):
        update_channel = self.settings.getChannel(member.guild.id)
        if update_channel is None:
            return

        channel_obj = member.guild.get_channel(update_channel)
        strikes = self.settings.countUserStrikes(member.guild.id, member.id)
        if strikes:
            msg = 'Hey @here a user with {} strikes just joined the server: {}'.format(
                strikes, member.mention)
            await channel_obj.send(msg)

        local_ban = self.settings.bannedUsers().get(member.id, None)
        if local_ban:
            msg = 'Hey @here locally banned user {} (for: {}) just joined the server'.format(
                member.mention, local_ban)
            await channel_obj.send(msg)

    @commands.Cog.listener('on_member_update')
    async def check_punishment(self, before, after):
        if before.roles == after.roles:
            return

        new_roles = set(after.roles).difference(before.roles)
        removed_roles = set(before.roles).difference(after.roles)

        bad_role_ids = self.settings.getPunishmentRoles(after.guild.id)
        positive_role_ids = self.settings.getPositiveRoles(after.guild.id)
        neutral_role_ids = self.settings.getNeutralRoles(after.guild.id)

        for role in new_roles:
            if role.id in bad_role_ids:
                await self.recordBadUser(after, role.name)
                return

            if role.id in positive_role_ids:
                await self.recordRoleChange(after, role.name, True)
                return

            if role.id in neutral_role_ids:
                await self.recordRoleChange(after, role.name, True, send_ping=False)
                return

        for role in removed_roles:
            if role.id in positive_role_ids:
                await self.recordRoleChange(after, role.name, False)
                return
            if role.id in neutral_role_ids:
                await self.recordRoleChange(after, role.name, False, send_ping=False)
                return

    async def recordBadUser(self, member, role_name):
        latest_messages = self.logs.get(member.id, "")
        msg = 'Name={} Nick={} ID={} Joined={} Role={}\n'.format(
            member.name, member.nick, member.id, member.joined_at, role_name)
        msg += '\n'.join(latest_messages)
        self.settings.updateBadUser(member.guild.id, member.id, msg)
        strikes = self.settings.countUserStrikes(member.guild.id, member.id)

        update_channel = self.settings.getChannel(member.guild.id)
        if update_channel is not None:
            channel_obj = member.guild.get_channel(update_channel)
            await channel_obj.send(inline('Detected bad user'))
            await channel_obj.send(box(msg))
            await channel_obj.send('Hey @here please leave a note explaining why this user is punished')
            await channel_obj.send('This user now has {} strikes'.format(strikes))

            try:
                dm_msg = ('You were assigned the punishment role "{}" in the server "{}".\n'
                          'The Mods will contact you shortly regarding this.\n'
                          'Attempting to clear this role yourself will result in punishment.').format(role_name,
                                                                                                      member.guild.name)
                await member.send(box(dm_msg))
                await channel_obj.send('User successfully notified')
            except Exception as e:
                await channel_obj.send('Failed to notify the user! I might be blocked\n' + box(str(e)))

    async def recordRoleChange(self, member, role_name, is_added, send_ping=True):
        msg = 'Detected role {} : Name={} Nick={} ID={} Joined={} Role={}'.format(
            "Added" if is_added else "Removed", member.name, member.nick, member.id, member.joined_at, role_name)

        update_channel = self.settings.getChannel(member.guild.id)
        if update_channel is not None:
            channel_obj = member.guild.get_channel(update_channel)
            try:
                await channel_obj.send(inline(msg))
                if send_ping:
                    await channel_obj.send('Hey @here please leave a note explaining why this role was modified')
            except:
                print('Failed to notify in', update_channel, msg)


class BadUserSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'servers': {},
            'banned_users': {}
        }
        return config

    def serverConfigs(self):
        return self.bot_settings['servers']

    def getServer(self, server_id):
        configs = self.serverConfigs()
        if server_id not in configs:
            configs[server_id] = {}
        return configs[server_id]

    def getBadUsers(self, server_id):
        server = self.getServer(server_id)
        if 'badusers' not in server:
            server['badusers'] = {}
        return server['badusers']

    def getPunishmentRoles(self, server_id):
        server = self.getServer(server_id)
        if 'role_ids' not in server:
            server['role_ids'] = []
        return server['role_ids']

    def addPunishmentRole(self, server_id, role_id):
        role_ids = self.getPunishmentRoles(server_id)
        if role_id not in role_ids:
            role_ids.append(role_id)
        self.save_settings()

    def rmPunishmentRole(self, server_id, role_id):
        role_ids = self.getPunishmentRoles(server_id)
        if role_id in role_ids:
            role_ids.remove(role_id)
        self.save_settings()

    def getPositiveRoles(self, server_id):
        server = self.getServer(server_id)
        if 'positive_role_ids' not in server:
            server['positive_role_ids'] = []
        return server['positive_role_ids']

    def addPositiveRole(self, server_id, role_id):
        role_ids = self.getPositiveRoles(server_id)
        if role_id not in role_ids:
            role_ids.append(role_id)
        self.save_settings()

    def rmPositiveRole(self, server_id, role_id):
        role_ids = self.getPositiveRoles(server_id)
        if role_id in role_ids:
            role_ids.remove(role_id)
        self.save_settings()

    def addNeutralRole(self, server_id, role_id):
        role_ids = self.getNeutralRoles(server_id)
        if role_id not in role_ids:
            role_ids.append(role_id)
        self.save_settings()

    def getNeutralRoles(self, server_id):
        server = self.getServer(server_id)
        if 'neutral_role_ids' not in server:
            server['neutral_role_ids'] = []
        return server['neutral_role_ids']

    def rmNeutralRole(self, server_id, role_id):
        role_ids = self.getNeutralRoles(server_id)
        if role_id in role_ids:
            role_ids.remove(role_id)
        self.save_settings()

    def updateBadUser(self, server_id, user_id, msg):
        badusers = self.getBadUsers(server_id)
        if user_id not in badusers:
            badusers[user_id] = []

        badusers[user_id].append(msg)
        self.save_settings()

    def countUserStrikes(self, server_id, user_id):
        badusers = self.getBadUsers(server_id)
        if user_id not in badusers:
            return 0
        else:
            return len(badusers[user_id])

    def setUserStrikes(self, server_id, user_id, strikes):
        badusers = self.getBadUsers(server_id)
        badusers[user_id] = strikes
        self.save_settings()

    def clearUserStrikes(self, server_id, user_id):
        badusers = self.getBadUsers(server_id)
        badusers.pop(user_id, None)
        self.save_settings()

    def getUserStrikes(self, server_id, user_id):
        badusers = self.getBadUsers(server_id)
        return badusers.get(user_id, [])

    def updateChannel(self, server_id, channel_id):
        server = self.getServer(server_id)
        if channel_id is None:
            if 'update_channel' in server:
                server.pop('update_channel')
                self.save_settings()
            return

        server['update_channel'] = channel_id
        self.save_settings()

    def getChannel(self, server_id):
        server = self.getServer(server_id)
        return server.get('update_channel')

    def getStrikesPrivate(self, server_id):
        server = self.getServer(server_id)
        return server.get('strikes_private', False)

    def setStrikesPrivate(self, server_id, strikes_private):
        server = self.getServer(server_id)
        server['strikes_private'] = strikes_private
        self.save_settings()

    def bannedUsers(self):
        return self.bot_settings['banned_users']

    def addBannedUser(self, user_id: int, reason: str):
        self.bannedUsers()[user_id] = reason
        self.save_settings()

    def rmBannedUser(self, user_id: int):
        self.bannedUsers().pop(user_id, None)
        self.save_settings()
