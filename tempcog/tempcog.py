import logging
from io import BytesIO

from redbot.core import Config, commands

logger = logging.getLogger('red.padbot-cogs.tempcog')


class TempCog(commands.Cog):
    """Temporary Utilities."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=7379306)

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    @commands.Cog.listener('on_member_join')
    async def mod_user_join(self, member):
        if member.guild.id == 89391974502649856:
            await self.bot.get_channel(263512015635611650).send(
                "{0.mention} Join name: {0.name} ({0.id})"
                " joined the server. Created: {0.created_at}".format(member))

        if member.guild.id == 435913115750629377:
            await self.bot.get_channel(647601840891887641).send(
                "{0.mention} Join name: {0.name} ({0.id})"
                " joined the server. Created: {0.created_at}".format(member))
            
        if member.guild.id == 243014364129525760:
            await self.bot.get_channel(362777217349976065).send(
                "{0.mention} Join name: {0.name} ({0.id})"
                " joined the server. Created: {0.created_at}".format(member))
            
