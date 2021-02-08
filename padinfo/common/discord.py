import random

from discord import Color


def user_color_to_discord_color(color):
    if color is None:
        return Color.default()
    elif color == "random":
        return Color(random.randint(0x000000, 0xffffff))
    else:
        return Color(color)
