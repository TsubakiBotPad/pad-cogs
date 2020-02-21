import asyncio

import discord
from google.cloud import texttospeech
from google.oauth2 import service_account
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import inline

from rpadutils import CogSettings

try:
    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus-0.dll')
except:  # Missing opus
    print('Failed to load opus')
    opus = None
else:
    opus = True

SPOOL_PATH = "data/speech/spool.mp3"


class Speech(commands.Cog):
    """Speech utilities."""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = SpeechSettings("speech")

        self.service = None
        self.try_setup_api()
        self.busy = False

    def try_setup_api(self):
        api_key_file = self.settings.get_key_file()
        if api_key_file:
            try:
                credentials = service_account.Credentials.from_service_account_file(api_key_file)
                self.service = texttospeech.TextToSpeechClient(credentials=credentials)
            except:
                print('speech setup failed')

    @commands.group()
    @checks.is_owner()
    async def speech(self, ctx):
        """Speech utilities."""

    @commands.command()
    @checks.is_owner()
    async def vcsay(self, ctx, *, text):
        """Speak into the current user's voice channel."""
        if not self.service:
            await ctx.send(inline('Set up an API key file first!'))
            return

        voice = ctx.author.voice
        if not voice:
            await ctx.send(inline('You must be in a voice channel to use this command'))
            return

        channel = voice.voice_channel

        if len(text) > 300:
            await ctx.send(inline('Command is too long'))
            return

        await self.speak(ctx, channel, text)

    async def speak(self, ctx, channel, text: str):
        if self.busy:
            await ctx.send(inline('Sorry, saying something else right now'))
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
        existing_vc = self.bot.voice_client_in(channel.guild)
        if existing_vc:
            await existing_vc.disconnect()

        voice_client = None
        try:
            voice_client = await channel.connect()

            options = "-filter \"volume=volume=0.3\""

            audio_source = discord.FFmpegPCMAudio(audio_path, options=options)
            voice_client.play(audio_source)

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

    @speech.command()
    @checks.is_owner()
    async def setkeyfile(self, ctx, api_key_file):
        """Sets the google api key file."""
        self.settings.set_key_file(api_key_file)
        await ctx.send("done, make sure the key file is in the data/speech directory")


class SpeechSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'google_api_key_file': ''
        }
        return config

    def get_key_file(self):
        return self.bot_settings.get('google_api_key_file')

    def set_key_file(self, api_key_file):
        self.bot_settings['google_api_key_file'] = api_key_file
        self.save_settings()
