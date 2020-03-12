import json
import re
from fnmatch import fnmatch

from ply import lex
from redbot.core import checks
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, pagify

from rpadutils import rpadutils

class Playground(commands.Cog):
    """Just lil' fun things."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
