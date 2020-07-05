import discord
import romkan

from googleapiclient.discovery import build
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import inline

from rpadutils import CogSettings


class Translate(commands.Cog):
    """Translation utilities."""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=724757473)
        self.config.register_global(api_key=None)

        self.service = None


    @commands.group()
    @checks.is_owner()
    async def translate(self, context):
        """Translation utilities."""


    @translate.command()
    async def build_service(self):
        api_key = await self.config.api_key()
        try:
            assert api_key
            self.service = build('translate', 'v2', developerKey=api_key)
        except:
            print("Google API key not found or invalid")


    @commands.command(aliases=['jaus', 'jpen', 'jpus'])
    async def jaen(self, ctx, *, query):
        """Translates from Japanese to English"""
        if not self.service:
            await ctx.send(inline('Set up an API key first!'))
            return

        em = self.translate_to_embed("ja", "en", query)
        await ctx.send(embed=em)

    @commands.command(aliases=['zhus'])
    async def zhen(self, ctx, *, query):
        """Translates from Chinese to English"""
        if not self.service:
            await ctx.send(inline('Set up an API key first!'))
            return

        em = self.translate_to_embed("zh", "en", query)
        await ctx.send(embed=em)

    @commands.command()
    async def kanrom(self, ctx, *, query):
        """Transliterates Kanji to Romanji"""
        await ctx.send(romkan.to_roma(query))


    def translate_lang(self, source, target, query):
        result = self.service.translations().list(source=source, target=target, format='text', q=query).execute()
        return result.get('translations')[0].get('translatedText')

    def translate_to_embed(self, source, target, query):
        translation = self.translate_lang(source, target, query)
        return discord.Embed(description='**Original**\n`{}`\n\n**Translation**\n`{}`'.format(query, translation))

    @translate.command()
    async def setkey(self, ctx, api_key):
        """Sets the google api key."""
        await self.config.api_key.set(api_key)
        await ctx.send(inline("done"))

    @translate.command()
    async def getkey(self, ctx):
        await ctx.author.send(await self.config.api_key())
