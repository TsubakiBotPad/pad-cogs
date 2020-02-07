from .voicerole import *


def setup(bot):
    n = VoiceRole(bot)
    bot.add_cog(n)
    bot.add_listener(n.on_voice_state_update, 'on_voice_state_update')
