from collections import defaultdict
import os
import re

import discord
from discord.ext import commands
from googleapiclient.discovery import build

from __main__ import user_allowed, send_cmd_help

from .rpadutils import *
from .rpadutils import CogSettings
from .utils import checks
from .utils.dataIO import dataIO


class Translate:
    """Translation utilities."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = TranslateSettings("translate")

        self.service = None
        self.trySetupService()

    def trySetupService(self):
        api_key = self.settings.getKey()
        if api_key:
            self.service = build('translate', 'v2', developerKey=api_key)

    async def checkAutoTranslateJp(self, message):
        if (message.channel.is_private
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
                await self.bot.send_message(message.channel, embed=em)

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def translate(self, context):
        """Translation utilities."""
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @commands.command(pass_context=True, aliases=['jaus', 'jpen', 'jpus'])
    async def jaen(self, ctx, *, query):
        """Translates from Japanese to English"""
        if not self.service:
            await self.bot.say(inline('Set up an API key first!'))
            return

        em = self.translateToEmbed(query)
        await self.bot.say(embed=em)

    def translate_jp_en(self, query):
        result = self.service.translations().list(source='ja', target='en', format='text', q=query).execute()
        return result.get('translations')[0].get('translatedText')

    def translateToEmbed(self, query):
        translation = self.translate_jp_en(query)
        return discord.Embed(description='**Original**\n`{}`\n\n**Translation**\n`{}`'.format(query, translation))

    @translate.command(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def autotranslatejp(self, ctx, channel: discord.Channel=None):
        channel = channel if channel else ctx.message.channel
        if channel.id in self.settings.autoTranslateJp():
            self.settings.rmAutoTranslateJp(channel.id)
            await self.bot.say(inline('Removed {} from Japanese auto translate'.format(channel.name)))
        else:
            self.settings.addAutoTranslateJp(channel.id)
            await self.bot.say(inline('Added {} to Japanese auto translate'.format(channel.name)))

    @translate.command(pass_context=True)
    @checks.is_owner()
    async def setkey(self, ctx, api_key):
        """Sets the google api key."""
        self.settings.setKey(api_key)
        await self.bot.say("done")


def setup(bot):
    n = Translate(bot)
    bot.add_listener(n.checkAutoTranslateJp, "on_message")
    bot.add_cog(n)


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
