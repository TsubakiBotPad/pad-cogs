import asyncio
import concurrent.futures
import inspect
import json
import os
import re
import time
import unicodedata
import urllib
from functools import wraps
import errno
import signal

import aiohttp
import backoff
import pytz
from discord.ext.commands import CommandNotFound
from redbot.core import commands, data_manager
from redbot.core.utils.chat_formatting import *


class RpadUtils(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    async def on_command_error(self, ctx, error):
        channel = ctx.channel
        if isinstance(error, ReportableError):
            msg = 'An error occurred while processing your command: {}'.format(error.message)
            await channel.send(inline(msg))

    def user_allowed(self, message):
        author = message.author

        if author.bot:
            return False
        """
        mod_cog = self.bot.get_cog('Mod')

        if not isinstance(message.channel, discord.abc.PrivateChannel):
            guild = message.guild
            names = (self.bot.settings.get_server_admin(
                guild), self.bot.settings.get_server_mod(guild))
            results = map(
                lambda name: discord.utils.get(author.roles, name=name),
                names)
            for r in results:
                if r is not None:
                    return True

        if mod_cog is not None:
            if not isinstance(message.channel, discord.abc.PrivateChannel):
                if message.guild.id in mod_cog.ignore_list["SERVERS"]:
                    return False

                if message.channel.id in mod_cog.ignore_list["CHANNELS"]:
                    return False
        """
        return True


# TZ used for PAD NA
# NA_TZ_OBJ = pytz.timezone('America/Los_Angeles')
NA_TZ_OBJ = pytz.timezone('US/Pacific')

# TZ used for PAD JP
JP_TZ_OBJ = pytz.timezone('Asia/Tokyo')

# https://gist.github.com/ryanmcgrath/982242
# UNICODE RANGE : DESCRIPTION
# 3000-303F : punctuation
# 3040-309F : hiragana
# 30A0-30FF : katakana
# FF00-FFEF : Full-width roman + half-width katakana
# 4E00-9FAF : Common and uncommon kanji
#
# Non-Japanese punctuation/formatting characters commonly used in Japanese text
# 2605-2606 : Stars
# 2190-2195 : Arrows
# u203B     : Weird asterisk thing

JP_REGEX_STR = r'[\u3000-\u303F]|[\u3040-\u309F]|[\u30A0-\u30FF]|[\uFF00-\uFFEF]|[\u4E00-\u9FAF]|[\u2605-\u2606]|[\u2190-\u2195]|\u203B'
JP_REGEX = re.compile(JP_REGEX_STR)


def containsJp(txt):
    return JP_REGEX.search(txt)


class ReportableError(commands.CheckFailure):
    """Throw when an exception should be reported to the user."""

    def __init__(self, message):
        self.message = message
        super(ReportableError, self).__init__(message)


class PermissionsError(CommandNotFound):
    """
    Base exception for all others in this module
    """


class BadCommand(PermissionsError):
    """
    Thrown when we can't decipher a command from string into a command object.
    """
    pass


class RoleNotFound(PermissionsError):
    """
    Thrown when we can't get a valid role from a list and given name
    """
    pass


class SpaceNotation(BadCommand):
    """
    Throw when, with some certainty, we can say that a command was space
        notated, which would only occur when some idiot...fishy...tries to
        surround a command in quotes.
    """
    pass


def get_role(roles, role_string):
    if role_string.lower() == "everyone":
        role_string = "@everyone"

    role = discord.utils.find(
        lambda r: r.name.lower() == role_string.lower(), roles)

    if role is None:
        print("Could not find role named " + role_string)
        raise ReportableError("Could not find role named " + role_string)

    return role


def get_role_from_id(bot, guild, roleid):
    try:
        roles = guild.roles
    except AttributeError:
        guild = get_server_from_id(bot, guild)
        try:
            roles = guild.roles
        except AttributeError:
            raise RoleNotFound(guild, roleid)

    role = discord.utils.get(roles, id=roleid)
    if role is None:
        raise ReportableError("Could not find role id {} in guild {}".format(roleid, guild.name))
    return role


def get_server_from_id(bot, serverid):
    return discord.utils.get(bot.guilds, id=serverid)


def normalizeServer(server):
    server = server.upper()
    return 'NA' if server == 'US' else server


def should_download(file_path, expiry_secs):
    if not os.path.exists(file_path):
        print("file does not exist, downloading " + file_path)
        return True

    ftime = os.path.getmtime(file_path)
    file_age = time.time() - ftime
    print("for " + file_path + " got " + str(ftime) + ", age " +
          str(file_age) + " against expiry of " + str(expiry_secs))

    if file_age > expiry_secs:
        print("file too old, download it")
        return True
    else:
        return False


def writeJsonFile(file_path, js_data):
    with open(file_path, "w") as f:
        json.dump(js_data, f, indent=4)


def readJsonFile(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def safe_read_json(file_path):
    try:
        return readJsonFile(file_path)
    except Exception as ex:
        print('failed to read', file_path, 'got exception', ex)
    return {}


def ensure_json_exists(file_dir, file_name):
    if not os.path.exists(file_dir):
        print("Creating dir: ", file_dir)
        os.makedirs(file_dir)
    file_path = os.path.join(file_dir, file_name)
    try:
        readJsonFile(file_path)
    except:
        print('File missing or invalid json:', file_path)
        writeJsonFile(file_path, {})


@backoff.on_exception(backoff.expo, aiohttp.ClientError, max_time=60)
@backoff.on_exception(backoff.expo, aiohttp.ServerDisconnectedError, max_time=60)
async def async_cached_dadguide_request(file_path, file_url, expiry_secs):
    if should_download(file_path, expiry_secs):
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                assert resp.status == 200
                with open(file_path, 'wb') as f:
                    f.write(await resp.read())


def writePlainFile(file_path, text_data):
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(text_data)


def readPlainFile(file_path):
    with open(file_path, "r", encoding='utf-8') as f:
        return f.read()


def makePlainRequest(file_url):
    response = urllib.request.urlopen(file_url)
    data = response.read()  # a `bytes` object
    return data.decode('utf-8')


async def makeAsyncPlainRequest(file_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            return await resp.text()


async def makeAsyncCachedPlainRequest(file_path, file_url, expiry_secs):
    if should_download(file_path, expiry_secs):
        resp = await makeAsyncPlainRequest(file_url)
        writePlainFile(file_path, resp)
    return readPlainFile(file_path)


async def boxPagifySay(say_fn, msg):
    for page in pagify(msg, delims=["\n"]):
        await say_fn(box(page))


class Forbidden():
    pass


def default_check(payload):
    return not payload.member.bot


class EmojiUpdater(object):
    # a pass-through class that does nothing to the emoji dictionary
    # or to the selected emoji
    def __init__(self, emoji_to_embed, **kwargs):
        self.emoji_dict = emoji_to_embed
        self.selected_emoji = None

    def on_update(self, ctx, selected_emoji):
        self.selected_emoji = selected_emoji
        return True


class Menu():
    def __init__(self, bot):
        self.bot = bot

        # Feel free to override this in your cog if you need to
        self.emoji = {
            0: "0⃣",
            1: "1⃣",
            2: "2⃣",
            3: "3⃣",
            4: "4⃣",
            5: "5⃣",
            6: "6⃣",
            7: "7⃣",
            8: "8⃣",
            9: "9⃣",
            10: "🔟",
            "next": "➡",
            "back": "⬅",
            "yes": "✅",
            "no": "❌",
        }

    # for use as an action
    async def reaction_delete_message(self, bot, ctx, message):
        await message.delete()

    #     def perms(self, ctx):
    #         user = ctx.guild.get_member(int(self.bot.user.id))
    #         return ctx.channel.permissions_for(user)

    async def custom_menu(self, ctx, emoji_to_message, selected_emoji, **kwargs):
        """Creates and manages a new menu
        Required arguments:
            Type:
                1- number menu
                2- confirmation menu
                3- info menu (basically menu pagination)
                4- custom menu. If selected, choices must be a list of tuples.
            Messages:
                Strings or embeds to use for the menu.
                Pass as a list for number menu
        Optional arguments:
            page (Defaults to 0):
                The message in messages that will be displayed
            timeout (Defaults to 15):
                The number of seconds until the menu automatically expires
            check (Defaults to default_check):
                The same check that wait_for_reaction takes
            is_open (Defaults to False):
                Whether or not the menu can take input from any user
            emoji (Defaults to self.emoji):
                A dictionary containing emoji to use for the menu.
                If you pass this, use the same naming scheme as self.emoji
            message (Defaults to None):
                The discord.Message to edit if present
            """
        return await self._custom_menu(ctx, emoji_to_message, selected_emoji, **kwargs)

    async def show_menu(self,
                        ctx,
                        message,
                        new_message_content):
        if message:
            if isinstance(new_message_content, discord.Embed):
                return await message.edit(embed=new_message_content)
            else:
                return await message.edit(content=new_message_content)
        else:
            if isinstance(new_message_content, discord.Embed):
                return await ctx.send(embed=new_message_content)
            else:
                return await ctx.send(new_message_content)

    async def _custom_menu(self, ctx, emoji_to_message, selected_emoji,
                           allowed_action=True, **kwargs):
        timeout = kwargs.get('timeout', 15)
        message = kwargs.get('message', None)

        reactions_required = not message
        new_message_content = emoji_to_message.emoji_dict[selected_emoji]
        if allowed_action:
            if not message:
                message = await self.show_menu(ctx, message, new_message_content)
            else:
                await self.show_menu(ctx, message, new_message_content)

        if reactions_required:
            for e in emoji_to_message.emoji_dict:
                try:
                    await message.add_reaction(e)
                except Exception as e:
                    # failed to add reaction, ignore
                    pass

        def check(payload):
            return kwargs.get('check', default_check)(payload) and \
                   str(payload.emoji.name) in list(emoji_to_message.emoji_dict.keys()) and \
                   payload.user_id == ctx.author.id and \
                   payload.message_id == message.id

        if not message:
            raise ValueError(message, ctx)
            return None, None

        try:
            p = await self.bot.wait_for('raw_reaction_add', check=check, timeout=timeout)
        except Exception as e:
            p = None

        if p is None:
            try:
                await message.clear_reactions()
            except Exception as e:
                # This is expected when miru doesn't have manage messages
                pass
            return message, new_message_content

        react_emoji = p.emoji.name
        react_action = emoji_to_message.emoji_dict[p.emoji.name]

        if inspect.iscoroutinefunction(react_action):
            message = await react_action(self.bot, ctx, message)
        elif inspect.isfunction(react_action):
            message = react_action(ctx, message)

        # user function killed message, quit
        if not message:
            return None, None

        try:
            await message.remove_reaction(react_emoji, p.member)
        except:
            # This is expected when miru doesn't have manage messages
            pass

        # update the emoji mapping however we need to, or just pass through and do nothing

        allowed_action = emoji_to_message.on_update(ctx, react_emoji)
        return await self._custom_menu(
            ctx, emoji_to_message, emoji_to_message.selected_emoji,
            timeout=timeout,
            check=check,
            message=message,
            allowed_action=allowed_action)


def char_to_emoji(c):
    c = c.lower()
    if c >= '0' and c <= '9':
        names = {
            '0': '0⃣',
            '1': '1⃣',
            '2': '2⃣',
            '3': '3⃣',
            '4': '4⃣',
            '5': '5⃣',
            '6': '6⃣',
            '7': '7⃣',
            '8': '8⃣',
            '9': '9⃣',
        }
        return names[c]
    if c < 'a' or c > 'z':
        return c

    base = ord('\N{REGIONAL INDICATOR SYMBOL LETTER A}')
    adjustment = ord(c) - ord('a')
    return chr(base + adjustment)


##############################
# Hack to fix discord.py
##############################
# TODO: check if this is still needed
# class UserConverter2(converter.IDConverter):
#     @asyncio.coroutine
#     def convert(self, ctx, argument):
#         message = ctx.message
#         bot = ctx.bot
#         match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
#         server = message.guild
#         result = None
#         if match is None:
#             # not a mention...
#             if server:
#                 result = server.get_member_named(argument)
#             else:
#                 result = _get_from_servers(bot, 'get_member_named', argument)
#         else:
#             user_id = match.group(1)
#             if server:
#                 result = yield from bot.fetch_user(int(user_id))
#             else:
#                 result = _get_from_servers(bot, 'get_member', user_id)
#
#         if result is None:
#             raise BadArgument('Member "{}" not found'.format(argument))
#
#         return result
#
#
# converter.UserConverter = UserConverter2


##############################
# End hack to fix discord.py
##############################


def fix_emojis_for_server(emoji_list, msg_text):
    """Finds 'emoji-looking' substrings in msg_text and corrects them.

    If msg_text has something like '<:emoji_1_derp:13242342343>' and the server
    contains an emoji named :emoji_2_derp: then it will be swapped out in
    the message.

    This corrects an issue where a padglobal alias is created in one server
    with an emoji, but it has a slightly different name in another server.
    """
    # Find all emoji-looking things in the message
    matches = re.findall(r'<:[0-9a-z_]+:\d{18}>', msg_text, re.IGNORECASE)
    if not matches:
        return msg_text

    # For each unique looking emoji thing
    for m in set(matches):
        # Create a regex for that emoji replacing the digit
        m_re = re.sub(r'\d', r'\d', m)
        for em in emoji_list:
            # If the current emoji matches the regex, force a replacement
            emoji_code = str(em)
            if re.match(m_re, emoji_code, re.IGNORECASE):
                msg_text = re.sub(m_re, emoji_code, msg_text, flags=re.IGNORECASE)
                break
    return msg_text


def replace_emoji_names_with_code(emoji_list, msg_text):
    """Finds emoji-name substrings in msg_text and corrects them.

    If msg_text has something like ':emoji_1_derp:' and emoji_list contains
    an emoji named 'emoji_1_derp' then the value will replaced with the full
    emoji id.

    This allows a padglobal admin without nitro to create entries with emojis
    from other servers.
    """
    # First strip down actual emojis to just the names
    msg_text = re.sub(r'<(:[0-9a-z_]+:)\d{18}>', r'\1', msg_text, flags=re.IGNORECASE)

    # Find all emoji-looking things in the message
    matches = re.findall(r':[0-9a-z_]+:', msg_text, re.IGNORECASE)
    if not matches:
        return msg_text

    # For each unique looking emoji thing
    for m in set(matches):
        emoji_name = m.strip(':')
        for e in emoji_list:
            if e.name == emoji_name:
                msg_text = msg_text.replace(m, str(e))
    return msg_text


def is_valid_image_url(url):
    url = url.lower()
    return url.startswith('http') and (url.endswith('.png') or url.endswith('.jpg'))


def extract_image_url(m):
    if is_valid_image_url(m.content):
        return m.content
    if m.attachments and len(m.attachments) and is_valid_image_url(m.attachments[0].url):
        return m.attachments[0].url
    return None


def rmdiacritics(input):
    '''
    Return the base character of char, by "removing" any
    diacritics like accents or curls and strokes and the like.
    '''
    output = ''
    for c in input:
        try:
            desc = unicodedata.name(c)
            cutoff = desc.find(' WITH ')
            if cutoff != -1:
                desc = desc[:cutoff]
            output += unicodedata.lookup(desc)
        except:
            output += c
    return output


def clean_global_mentions(content):
    """Wipes out mentions to @everyone and @here."""
    return re.sub(r'(@)(\w)', '\\g<1>\u200b\\g<2>', content)


def intify(iterable):
    if isinstance(iterable, dict):
        for item in list(iterable):
            try:
                iterable[int(item)] = intify(iterable[item])
            except:
                iterable[item] = intify(iterable[item])
    elif isinstance(iterable, (list, tuple)):
        for item in iterable:
            if intify(item) != item:
                iterable.append(intify(item))
    return iterable


class CogSettings(object):
    SETTINGS_FILE_NAME = "legacy_settings.json"

    def __init__(self, cog_name):
        self.folder = str(data_manager.cog_data_path(raw_name=cog_name))
        self.file_path = os.path.join(self.folder, CogSettings.SETTINGS_FILE_NAME)

        self.check_folder()

        self.default_settings = self.make_default_settings()
        if not os.path.isfile(self.file_path):
            self.bot_settings = self.default_settings
            self.save_settings()
        else:
            current = intify(readJsonFile(self.file_path))
            updated = False
            for key in self.default_settings.keys():
                if key not in current.keys():
                    current[key] = self.default_settings[key]
                    updated = True

            self.bot_settings = current
            if updated:
                self.save_settings()

    def check_folder(self):
        if not os.path.exists(self.folder):
            print("Creating " + self.folder)
            os.makedirs(self.folder)

    def save_settings(self):
        writeJsonFile(self.file_path, self.bot_settings)

    def make_default_settings(self):
        return {}

    # TODO: maybe centralize get_server / get_server_channel stuff since i do that everywhere
    def getServerSettings(self, server_id):
        if 'cmd_whitelist_blacklist' not in self.bot_settings:
            self.bot_settings['cmd_whitelist_blacklist'] = {}

        settings = self.bot_settings['cmd_whitelist_blacklist']
        if server_id not in settings:
            settings[server_id] = {}

        return settings[server_id]


def get_prefix(bot, server, text):
    for p in bot.settings.get_prefixes(server):
        if text.startswith(p):
            return p
    return False


def strip_right_multiline(txt: str):
    """Useful for prettytable output where there is a lot of right spaces,"""
    return '\n'.join([x.strip() for x in txt.splitlines()])


# This was overwritten by voltron. PDX opted to copy it +10,000 ids away
CROWS_1 = {x: x + 10000 for x in range(2601, 2635 + 1)}
# This isn't overwritten but PDX adjusted anyway
CROWS_2 = {x: x + 10000 for x in range(3460, 3481 + 1)}

PDX_JP_ADJUSTMENTS = {}
PDX_JP_ADJUSTMENTS.update(CROWS_1)
PDX_JP_ADJUSTMENTS.update(CROWS_2)


def get_pdx_id(m):
    pdx_id = m.monster_no_na
    if int(m.monster_no) == m.monster_no_jp:
        pdx_id = PDX_JP_ADJUSTMENTS.get(pdx_id, pdx_id)
    return pdx_id


def get_pdx_id_dadguide(m):
    pdx_id = m.monster_no_na
    if int(m.monster_id) == m.monster_no_jp:
        pdx_id = PDX_JP_ADJUSTMENTS.get(pdx_id, pdx_id)
    return pdx_id


async def await_and_remove(bot, react_msg, listen_user, delete_msgs=None, emoji="❌", timeout=15):
    try:
        await react_msg.add_reaction(emoji)
    except Exception as e:
        # failed to add reaction, ignore
        return

    def check(payload):
        return str(payload.emoji.name) == emoji and \
               payload.user_id == listen_user.id and \
               payload.message_id == react_msg.id

    try:
        p = await bot.wait_for('add_reaction', check=check, timeout=timeout)
    except:
        # Expected after {timeout} seconds
        p = None

    if p is None:
        try:
            await react_msg.remove_reaction(emoji, react_msg.guild.me)
        except Exception as e:
            # failed to remove reaction, ignore
            return
    else:
        msgs = delete_msgs or [react_msg]
        for m in msgs:
            await m.delete_message()


loop_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


async def run_in_loop(bot, task, *args):
    event_loop = asyncio.get_event_loop()
    running_task = event_loop.run_in_executor(loop_executor, task, *args)
    return await running_task


async def translate_jp_en(bot, jp_text):
    translate_cog = bot.get_cog('Translate')
    if not translate_cog:
        return None
    return await run_in_loop(bot, translate_cog.translate_jp_en, jp_text)


def validate_json(fp):
    try:
        json.load(open(fp))
        return True
    except:
        return False


class TimeoutError(Exception):
    pass


def timeout_after(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL,seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return wraps(func)(wrapper)
    return decorator
