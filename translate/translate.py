import discord
from googleapiclient.discovery import build
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import inline

from rpadutils import CogSettings


class Translate(commands.Cog):
    """Translation utilities."""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = TranslateSettings("translate")

        self.service = None
        self.trySetupService()

    def trySetupService(self):
        api_key = self.settings.get_key()
        if api_key:
            self.service = build('translate', 'v2', developerKey=api_key)

    @commands.group()
    @checks.is_owner()
    async def translate(self, context):
        """Translation utilities."""

    @commands.command(aliases=['jaus', 'jpen', 'jpus'])
    async def jaen(self, ctx, *, query):
        """Translates from Japanese to English"""
        if not self.service:
            await ctx.send(inline('Set up an API key first!'))
            return

        em = self.translate_to_embed(query)
        await ctx.send(embed=em)

    def translate_jp_en(self, query):
        result = self.service.translations().list(source='ja', target='en', format='text', q=query).execute()
        return result.get('translations')[0].get('translatedText')

    def translate_to_embed(self, query):
        translation = self.translate_jp_en(query)
        return discord.Embed(description='**Original**\n`{}`\n\n**Translation**\n`{}`'.format(query, translation))

    @translate.command()
    @checks.is_owner()
    async def setkey(self, ctx, api_key):
        """Sets the google api key."""
        self.settings.set_key(api_key)
        await ctx.send("done")


class TranslateSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'google_api_key': ''
        }
        return config

    def get_key(self):
        return self.bot_settings.get('google_api_key')

    def set_key(self, api_key):
        self.bot_settings['google_api_key'] = api_key
        self.save_settings()
