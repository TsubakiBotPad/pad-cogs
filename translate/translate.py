from googleapiclient.discovery import build
from redbot.core import checks
from redbot.core import commands
from redbot.core.utils.chat_formatting import *

from rpadutils import CogSettings, containsJp


class Translate(commands.Cog):
    """Translation utilities."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = TranslateSettings("translate")

        self.service = None
        self.trySetupService()

    def trySetupService(self):
        api_key = self.settings.getKey()
        if api_key:
            self.service = build('translate', 'v2', developerKey=api_key)

    @commands.Cog.listener('on_message')
    async def checkAutoTranslateJp(self, message):
        if (isinstance(message.channel, discord.abc.PrivateChannel)
                or not self.service
                or message.channel.id not in self.settings.autoTranslateJp()
                or not containsJp(message.clean_content)):
            return

        for p in self.bot.settings.get_prefixes(message.server):
            if message.content.startswith(p):
                return

        message_parts = message.clean_content.split('```')
        for part in message_parts:
            if containsJp(part):
                em = self.translateToEmbed(part)
                await message.channel.send_message(embed=em)

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

        em = self.translateToEmbed(query)
        await ctx.send(embed=em)

    def translate_jp_en(self, query):
        result = self.service.translations().list(source='ja', target='en', format='text', q=query).execute()
        return result.get('translations')[0].get('translatedText')

    def translateToEmbed(self, query):
        translation = self.translate_jp_en(query)
        return discord.Embed(description='**Original**\n`{}`\n\n**Translation**\n`{}`'.format(query, translation))

    @translate.command()
    @checks.is_owner()
    @commands.guild_only()
    async def autotranslatejp(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        if channel.id in self.settings.autoTranslateJp():
            self.settings.rmAutoTranslateJp(channel.id)
            await ctx.send(inline('Removed {} from Japanese auto translate'.format(channel.name)))
        else:
            self.settings.addAutoTranslateJp(channel.id)
            await ctx.send(inline('Added {} to Japanese auto translate'.format(channel.name)))

    @translate.command()
    @checks.is_owner()
    async def setkey(self, ctx, api_key):
        """Sets the google api key."""
        self.settings.setKey(api_key)
        await ctx.send("done")


class TranslateSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'google_api_key': ''
        }
        return config

    def autoTranslateJp(self):
        key = 'auto_translate_jp'
        if key not in self.bot_settings:
            self.bot_settings[key] = []
        return self.bot_settings[key]

    def addAutoTranslateJp(self, channel_id):
        auto_translate_jp = self.autoTranslateJp()
        if channel_id not in auto_translate_jp:
            auto_translate_jp.append(channel_id)
            self.save_settings()

    def rmAutoTranslateJp(self, channel_id):
        auto_translate_jp = self.autoTranslateJp()
        if channel_id in auto_translate_jp:
            auto_translate_jp.remove(channel_id)
            self.save_settings()

    def getKey(self):
        return self.bot_settings.get('google_api_key')

    def setKey(self, api_key):
        self.bot_settings['google_api_key'] = api_key
        self.save_settings()
