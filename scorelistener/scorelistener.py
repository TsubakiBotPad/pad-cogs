import re
from io import BytesIO
from tsutils.cogs.globaladmin import auth_check
from redbot.core import Config, commands
from scorelistener.service_account import SERVICE_ACCOUNT
import firebase_admin
from firebase_admin import credentials, db


class ScoreListener(commands.Cog):
    """Saves crown cutoff scores"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=10100779)
        self.config.register_channel(enabled=False)
        gadmin = self.bot.get_cog("GlobalAdmin")
        if gadmin:
            gadmin.register_perm("contentadmin")

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    @commands.Cog.listener('on_message')
    async def on_message(self, message):
        channel = message.channel
        content = message.content
        if not await self.config.channel(channel).enabled():
            return
        if message.guild is None:  # dms
            return
        if message.author == self.bot.user:  # dont reply to self
            return
        if await self.is_command(message):  # skip commands
            return
        if not re.match(r"^(\d){2,3}[ ,]?(\d){3}$", content):  # invalid score
            return
        if not firebase_admin._apps:  # firebase instance not started
            api_keys = await self.bot.get_shared_api_tokens("firebase")
            if not api_keys["private_key"] or not api_keys["private_key_id"]:
                await channel.send("The API keys are missing.")
                return
            SERVICE_ACCOUNT["private_key"] = api_keys["private_key"][:-1].replace(".", " ")
            SERVICE_ACCOUNT["private_key_id"] = api_keys["private_key_id"]
            cred = credentials.Certificate(SERVICE_ACCOUNT)
            try:
                firebase_admin.initialize_app(cred, {
                    'databaseURL': "https://ranking-chart-default-rtdb.firebaseio.com"
                })
            except ValueError:
                await channel.send("The API keys are invalid.")

        crown_ref = db.reference("/nacrowndata/")
        max_date_ref = db.reference("/info/maxDate/")

        date_stamp = message.created_at.timestamp() * 1000
        if date_stamp >= max_date_ref.get():  # posting final cutoff
            date_stamp = max_date_ref.get()

        crown_ref.push(value={
            "date": date_stamp,
            "score": re.sub(r"[^0-9]", "", content)
        })
        await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @commands.group()
    async def scorelistener(self, ctx):
        """Commands pertaining to score listener"""

    @scorelistener.command()
    @auth_check('contentadmin')
    async def enable(self, ctx):
        """Enable score listener in this channel"""
        await self.config.channel(ctx.channel).enabled.set(True)
        await ctx.send("Enabled score listener in this channel.")

    @scorelistener.command()
    @auth_check('contentadmin')
    async def disable(self, ctx):
        """Disable score listener in this channel"""
        await self.config.channel(ctx.channel).enabled.set(False)
        await ctx.send("Disabled score listener in this channel.")

    @scorelistener.command()
    @auth_check('contentadmin')
    async def deleteapp(self, ctx):
        """Gracefully delete Firebase App instance"""
        try:
            firebase_admin.delete_app(firebase_admin.get_app())
            await ctx.tick()
        except ValueError:
            await ctx.send("App does not exist.")

    async def is_command(self, msg):
        prefixes = await self.bot.get_valid_prefixes()
        for p in prefixes:
            if msg.content.startswith(p):
                return True
        return False
