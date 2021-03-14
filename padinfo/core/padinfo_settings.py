from tsutils import CogSettings

HISTORY_DURATION = 11


class PadInfoSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'animation_dir': '',
            'alt_id_optout': [],
            'voice_dir_path': '',
            'emoji_use': {},
            'id_history': [],
        }
        return config

    def emojiServers(self):
        key = 'emoji_servers'
        if key not in self.bot_settings:
            self.bot_settings[key] = []
        return self.bot_settings[key]

    def setEmojiServers(self, emoji_servers):
        es = self.emojiServers()
        es.clear()
        es.extend(emoji_servers)
        self.save_settings()

    def setEvoID(self, user_id):
        if self.checkEvoID(user_id):
            return False
        self.bot_settings['alt_id_optout'].remove(user_id)
        self.save_settings()
        return True

    def rmEvoID(self, user_id):
        if not self.checkEvoID(user_id):
            return False
        self.bot_settings['alt_id_optout'].append(user_id)
        self.save_settings()
        return True

    def checkEvoID(self, user_id):
        return user_id not in self.bot_settings['alt_id_optout']

    def setVoiceDir(self, path):
        self.bot_settings['voice_dir_path'] = path
        self.save_settings()

    def voiceDir(self):
        return self.bot_settings['voice_dir_path']

    def log_emoji(self, emote):
        self.bot_settings['emoji_use'][emote] = self.bot_settings['emoji_use'].get(emote, 0) + 1
        self.save_settings()

    def log_id_result(self, monster_id: int):
        history = self.bot_settings['id_history']
        if monster_id in history:
            history.remove(monster_id)
        history.insert(0, monster_id)
        if len(history) > HISTORY_DURATION:
            history.pop()
        self.save_settings()

    def get_id_history(self):
        return self.bot_settings['id_history']

settings = PadInfoSettings("padinfo")
