from padinfo.common.discord import user_color_to_discord_color


class UserConfig:
    def __init__(self, color):
        self.color = color


class BotConfig:
    @staticmethod
    async def get_user(config, user_id):
        user_config = config.user_from_id(user_id)
        user_color = await user_config.color()
        color = user_color_to_discord_color(user_color)
        return UserConfig(color)
