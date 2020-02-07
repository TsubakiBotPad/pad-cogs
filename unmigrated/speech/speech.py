from collections import defaultdict
import io
import os
import re
import traceback

import discord
from discord.ext import commands
from google.oauth2 import service_account

from __main__ import user_allowed, send_cmd_help
from google.cloud import texttospeech

from .rpadutils import *
from .rpadutils import CogSettings
from .utils import checks
from .utils.dataIO import dataIO


try:
    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus-0.dll')
except:  # Missing opus
    print('Failed to load opus')
    opus = None
else:
    opus = True

SPOOL_PATH = "data/speech/spool.mp3"


class Speech:
    """Speech utilities."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = SpeechSettings("speech")

        self.service = None
        self.trySetupService()
        self.busy = False

    def trySetupService(self):
        api_key_file = self.settings.getKeyFile()
        if api_key_file:
            try:
                credentials = service_account.Credentials.from_service_account_file(api_key_file)
                self.service = texttospeech.TextToSpeechClient(credentials=credentials)
            except:
                print('speech setup failed')

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def speech(self, context):
        """Speech utilities."""
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def vcsay(self, ctx, *, text):
        """Speak into the current user's voice channel."""
        if not self.service:
            await self.bot.say(inline('Set up an API key file first!'))
            return

        voice = ctx.message.author.voice
        channel = voice.voice_channel
        if channel is None:
            await self.bot.say(inline('You must be in a voice channel to use this command'))
            return

        if len(text) > 300:
            await self.bot.say(inline('Command is too long'))
            return

        await self.speak(channel, text) 

    async def speak(self, channel, text: str):
        if self.busy:
            await self.bot.say(inline('Sorry, saying something else right now'))
            return False
        else:
            self.busy = True

        try:
            voice = texttospeech.types.VoiceSelectionParams(
                language_code='en-US', name='en-US-Wavenet-F')

            audio_config = texttospeech.types.AudioConfig(
                audio_encoding=texttospeech.enums.AudioEncoding.MP3)

            synthesis_input = texttospeech.types.SynthesisInput(text=text)
            response = self.service.synthesize_speech(synthesis_input, voice, audio_config)

            with open(SPOOL_PATH, 'wb') as out:
                out.write(response.audio_content)

            await self.play_path(channel, SPOOL_PATH)
            return True
        finally:
            self.busy = False
        return False

    async def play_path(self, channel, audio_path: str):
        existing_vc = self.bot.voice_client_in(channel.server)
        if existing_vc:
            await existing_vc.disconnect()

        voice_client = None
        try:
            voice_client = await self.bot.join_voice_channel(channel)

            use_avconv = False
            options = "-filter \"volume=volume=0.3\""

            audio_player = voice_client.create_ffmpeg_player(
                audio_path, use_avconv=use_avconv, options=options)
            audio_player.start()

            while not audio_player.is_done():
                await asyncio.sleep(0.01)

            await voice_client.disconnect()

            return True
        except Exception as e:
            if voice_client:
                try:
                    await voice_client.disconnect()
                except:
                    pass
            return False

    @speech.command(pass_context=True)
    @checks.is_owner()
    async def setkeyfile(self, ctx, api_key_file):
        """Sets the google api key file."""
        self.settings.setKeyFile(api_key_file)
        await self.bot.say("done, make sure the key file is in the data/speech directory")


def setup(bot):
    n = Speech(bot)
    bot.add_cog(n)


class SpeechSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'google_api_key_file': ''
        }
        return config

    def getKeyFile(self):
        return self.bot_settings.get('google_api_key_file')

    def setKeyFile(self, api_key_file):
        self.bot_settings['google_api_key_file'] = api_key_file
        self.save_settings()
