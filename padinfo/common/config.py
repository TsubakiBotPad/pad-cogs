from padinfo.common.discord import user_color_to_discord_color


class UserConfig:
    def __init__(self, color, beta_id3):
        self.color = color
        self.beta_id3 = beta_id3


class BotConfig:
    @staticmethod
    async def get_user(config, user_id):
        user_config = config.user_from_id(user_id)
        beta_id3 = await user_config.beta_id3()
        user_color = await user_config.color()
        color = user_color_to_discord_color(user_color)
        return UserConfig(color, beta_id3)
