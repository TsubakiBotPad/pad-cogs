import asyncio
from collections import defaultdict
from collections import deque
import copy
from datetime import datetime
import os
import random
import re
from time import time

import discord
from discord.ext import commands

from __main__ import send_cmd_help
from __main__ import settings

from .rpadutils import *
from .rpadutils import CogSettings
from .utils import checks
from .utils.chat_formatting import *
from .utils.dataIO import fileIO
from .utils.settings import Settings


MOD_HELP = """
Welcome to SuperMod!

This is a gag feature that allows you to automatically and temporarily elevate
users to 'moderator' status (SuperMods).

A SuperMod can do the following things via bot commands:
  * Rename a user
  * Put a user on 'quiet time'
  * Rename a discussion channel
  * Set the topic for a discussion channel

To set up SuperMod, you should:
  1) Create a mod-log channel.
  2) Tag this channel using supermod setModLogChannel
  3) Set the number of automatic SuperMods using supermod setSupermodCount
  4) Create a role for supermods.
  5) Tag this role using supermod setSupermodRole
  6) Tag 'discussion' channels using supermod addDiscussionChannel
  7) Ask the bot owner to enable your server
  8) Optionally set users as permanent SuperMods using supermod addPermanentSupermod

The mod-log channel should be world read-only and read-write for the bot..
Your SuperMod role should grant no privileges, except being hoisted.

When complete, the bot will start monitoring your discussion channels for activity.
Users who speak in a discussion channel will be entered into the potential SuperMod pool.

Periodically all non-permanent SuperMods will be removed.
Users will be automatically picked out of the active pool and promoted to SuperMod, and
the active pool is cleared (and will repopulate).

SuperMod actions are logged to the mod-log channel for auditing.

Users that misbehave can be disabled using supermod blacklist. This will lose their
SuperMod status and won't be selected as SuperMods in the future.

Users that can opt-out using supermod ignoreme. They will not be selected as SuperMods
and won't be affected by renames or quiet time.
"""

USER_HELP = """
SuperMods are automatically selected to moderate the server.

A SuperMod can do the following things via bot commands:
  * Rename another user
  * Put a user on 'quiet time'
  * Rename a discussion channel
  * Set the topic for a discussion channel

If you don't want to participate you can opt-out using supermod ignoreme. You will not be selected
as SuperMod, and won't be affected by renames or quiet time.
"""


REFRESH_STARTED = ":warning::octagonal_sign::warning::octagonal_sign: :regional_indicator_r: :regional_indicator_e: :regional_indicator_f: :regional_indicator_r: :regional_indicator_e: :regional_indicator_s: :regional_indicator_h: :clock1130::recycle::clock2: :recycle::regional_indicator_s: :regional_indicator_t: :regional_indicator_a: :regional_indicator_r: :regional_indicator_t: :regional_indicator_e: :regional_indicator_d::alarm_clock::stopwatch::alarm_clock::stopwatch: :ok_hand:"
REFRESH_REMOVED_QUIET = ":white_check_mark: :thumbsup: :octagonal_sign: Removed :sleeping: :sleepy: :zzz: :sleeping_accommodation: :regional_indicator_q: :regional_indicator_u: :regional_indicator_i: :regional_indicator_e: :regional_indicator_t:    :regional_indicator_t: :regional_indicator_i: :regional_indicator_m: :regional_indicator_e: :stopwatch: :alarm_clock: :clock: from :cartwheel: :point_right: :point_right: {} :point_left: :point_left: :ok_hand: :wave:"
REFRESH_REMOVED_SUPERMOD = ":broken_heart::no_entry_sign:removed :thumbsdown::x::sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles::cop: from :point_right: :point_right: {} :point_left: :point_left: :no_good: :ok_hand: :wave:"
REFRESH_ADDED_SUPERMOD = ":white_check_mark::ballot_box_with_check: added :heavy_plus_sign: :smiley: :sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: :cop: to :point_right: :point_right: {} :point_left: :point_left: :cartwheel: :ok_hand:"

USER_RENAME_FAILED_DISABLED = ":frowning: :frowning: :regional_indicator_s: :regional_indicator_o: :regional_indicator_r: :regional_indicator_r: :regional_indicator_y: :broken_heart: :sweat_drops: :sweat_drops: {}, :scream: :cold_sweat:  :point_right: :point_right: {} :point_left: :point_left: :rage: :rage: :rage: :regional_indicator_h: :regional_indicator_a: :regional_indicator_t: :regional_indicator_e: :regional_indicator_s: :rage: :rage: :rage: :sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: :cop: so :sparkling_heart: :sparkling_heart: :regional_indicator_i: :sparkling_heart: :sparkling_heart:  won't :person_frowning: :person_with_pouting_face: change :recycle: :arrow_forward: their :abc: :abcd: :capital_abcd: name :cold_sweat: :zipper_mouth:"
USER_RENAME_SUCCEEDED = ":sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: {} :arrow_forward: :arrow_heading_down: renamed :tophat: :eyeglasses: :point_right: :point_right: {} :point_left: :point_left: :arrow_heading_up: :recycle: to :point_right: :point_right: {} :point_left: :point_left: :white_check_mark: :ok_hand:"
USER_RENAME_CLEARED = ":sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: :cop: {} :octagonal_sign: :warning: cleared :recycle: :thumbsdown: :regional_indicator_n: :regional_indicator_i: :regional_indicator_c: :regional_indicator_k: :regional_indicator_n: :regional_indicator_a: :regional_indicator_m: :regional_indicator_e: for :zipper_mouth: :point_right: :point_right: {} :point_left: :point_left: :disappointed:"
USER_RENAME_FAILED = ":frowning: :frowning: :regional_indicator_s: :regional_indicator_o: :regional_indicator_r: :regional_indicator_r: :regional_indicator_y: :broken_heart: :sweat_drops: :sweat_drops: {} :heavy_multiplication_x: :rat: but :sparkling_heart: :sparkling_heart: :regional_indicator_i: :sparkling_heart: :sparkling_heart: :warning: couldn't :no_entry_sign: :x: change :recycle: :arrow_forward: the :regional_indicator_n: :regional_indicator_a: :regional_indicator_m: :regional_indicator_e: of :person_frowning: :frowning: :point_right: :point_right: {} :point_left: :point_left: :rage: :imp: to :clown: :cold_sweat: :point_right: :point_right: {} :point_left: :point_left: :sweat_drops: :thumbsdown:"

USER_QUIET_FAILED_DISABLED = ":frowning: :frowning: :regional_indicator_s: :regional_indicator_o: :regional_indicator_r: :regional_indicator_r: :regional_indicator_y: :broken_heart: :sweat_drops: :sweat_drops: {}, :point_right: :point_right: {} :point_left: :point_left: :rage: :rage: :rage: :regional_indicator_h: :regional_indicator_a: :regional_indicator_t: :regional_indicator_e: :regional_indicator_s: :rage: :rage: :rage: :sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: :cop: so :sparkling_heart: :sparkling_heart: :regional_indicator_i: :sparkling_heart: :sparkling_heart:  won't :no_entry_sign: :no_entry: put :point_right: :disappointed: them :family: :family_mmgb: in :sleeping: :sleepy: :zzz: :sleeping_accommodation: :regional_indicator_q: :regional_indicator_u: :regional_indicator_i: :regional_indicator_e: :regional_indicator_t:    :regional_indicator_t: :regional_indicator_i: :regional_indicator_m: :regional_indicator_e: :stopwatch: :alarm_clock: :clock:"
USER_QUIET_FAILED_SUPERMOD = ":frowning: :frowning: :regional_indicator_s: :regional_indicator_o: :regional_indicator_r: :regional_indicator_r: :regional_indicator_y: :broken_heart: :sweat_drops: :sweat_drops: {}, :point_right: :point_right: {} :point_left: :point_left: is :warning: :rolling_eyes: a :sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: :cop: :bangbang: :sparkling_heart: :sparkling_heart: :regional_indicator_i: :sparkling_heart: :sparkling_heart: :no_entry_sign: can't :no_pedestrians: :no_bicycles: :no_mobile_phones: :muscle:  put :family: :worried:  them :fist: :unamused: in :sleeping: :sleepy: :zzz: :sleeping_accommodation: :regional_indicator_q: :regional_indicator_u: :regional_indicator_i: :regional_indicator_e: :regional_indicator_t:    :regional_indicator_t: :regional_indicator_i: :regional_indicator_m: :regional_indicator_e: :stopwatch: :alarm_clock: :clock:"
USER_QUIET_SUCCEEDED = ":sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: :cop: {} :ok_hand: :muscle: put :cold_sweat: :point_right: :point_right: {} :point_left: :point_left: in :sleeping: :sleepy: :zzz: :sleeping_accommodation: :regional_indicator_q: :regional_indicator_u: :regional_indicator_i: :regional_indicator_e: :regional_indicator_t:    :regional_indicator_t: :regional_indicator_i: :regional_indicator_m: :regional_indicator_e: :stopwatch: :alarm_clock: :clock:"

CHANNEL_RENAME_SUCCEEDED = ":sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: :cop: {} :abc: :abcd: :capital_abcd: renamed :sunglasses: :ok_hand: channel :ear: :lips: :point_right: :point_right: {} :point_left: :point_left: to :arrow_forward: :railway_track: :point_right: :point_right: {} :point_left: :point_left: :ok_hand:"
CHANNEL_RENAME_FAILED = ":frowning: :frowning: :regional_indicator_s: :regional_indicator_o: :regional_indicator_r: :regional_indicator_r: :regional_indicator_y: :broken_heart: :sweat_drops: :sweat_drops:  {} :sparkling_heart: :sparkling_heart: :regional_indicator_i: :sparkling_heart: :sparkling_heart: :rage: can't :rage: :no_entry_sign: :abc: :abcd: :capital_abcd: rename :ocean: :no_bell: channel :point_right: :point_right: {} :point_left: :point_left: to :point_right: :point_right: {} :point_left: :point_left: It's :thumbsdown: :no_mobile_phones: not :imp: :face_palm: a :loudspeaker: :loudspeaker: discussion :loud_sound: :microphone2: channel :telephone: :no_mobile_phones: :ok_hand:"

CHANNEL_TOPIC_SUCCEEDED = ":sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: :cop:  {} :arrow_heading_up: :arrow_left: :recycle: changed :bookmark: :bookmark_tabs: channel :mouse_three_button: :ocean: topic :abc: :abcd: :capital_abcd: for :ok_hand: :point_right: :point_right: {} :point_left: :point_left: to :point_right: :point_right: {} :point_left: :point_left: :ok_hand:"
CHANNEL_TOPIC_FAILED = ":frowning: :frowning: :regional_indicator_s: :regional_indicator_o: :regional_indicator_r: :regional_indicator_r: :regional_indicator_y: :broken_heart: :sweat_drops: :sweat_drops:  {} :sparkling_heart: :sparkling_heart: :regional_indicator_i: :sparkling_heart: :sparkling_heart: :rage: can't :rage: :no_entry_sign: change  :abc: :abcd: :capital_abcd: channel :ocean: :no_bell: topic:motorcycle: :rocket:  for :point_right: :point_right: {} :point_left: :point_left: to :point_right: :point_right: {} :point_left: :point_left: It's :thumbsdown: :no_mobile_phones: not :imp: :face_palm: a :loudspeaker: :loudspeaker: discussion :loud_sound: :microphone2: channel :telephone: :no_mobile_phones: :ok_hand:"

USER_SET_IGNORE = ":sparkling_heart: :sparkling_heart: :regional_indicator_i: :sparkling_heart: :sparkling_heart: still :heart_decoration: :ok_hand: :heart_eyes: :regional_indicator_l: :regional_indicator_o: :regional_indicator_v: :regional_indicator_e: you :bangbang: :100: But  :sparkling_heart: :sparkling_heart: :regional_indicator_i: :sparkling_heart: :sparkling_heart: will :rage: :rage: ignore :sweat: :cold_sweat: you. :fire: :fire: :fire: :broken_heart: :broken_heart: :broken_heart: :regional_indicator_g: :regional_indicator_o: :regional_indicator_o: :regional_indicator_d: :regional_indicator_b: :regional_indicator_y: :regional_indicator_e: :point_right: :point_right: {} :point_left: :point_left: cannot :earth_africa: :earth_americas: :earth_asia: become :sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: :cop: :bangbang:"
USER_CLEARED_IGNORE = ":information_desk_person: :sweat_drops: :fireworks: :regional_indicator_s: :regional_indicator_e: :regional_indicator_n: :regional_indicator_p: :regional_indicator_a: :regional_indicator_i:  :wave:  :regional_indicator_n: :regional_indicator_o: :regional_indicator_t: :regional_indicator_i: :regional_indicator_c: :regional_indicator_e: :regional_indicator_d: :trophy:  :regional_indicator_y: :regional_indicator_o: :regional_indicator_u: :bangbang:  :sparkles:  :heart: :heart_eyes: {} :thumbsup: :ok_hand: can :sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: :cop: again :ballot_box_with_check: :white_check_mark: :sunny:"

BE_QUIET_1 = "{} :thinking: :zipper_mouth: you're :regional_indicator_n: :regional_indicator_o: :regional_indicator_t: :thumbsdown: :no_entry_sign: :no_entry: allowed :rage: :v: to :loud_sound: :loudspeaker: :loudspeaker: speak :ok_hand: :zipper_mouth: you're :zzz: :thumbsdown: in :sleeping: :sleepy: :zzz: :sleeping_accommodation: :regional_indicator_q: :regional_indicator_u: :regional_indicator_i: :regional_indicator_e: :regional_indicator_t:    :regional_indicator_t: :regional_indicator_i: :regional_indicator_m: :regional_indicator_e: :stopwatch: :alarm_clock: :clock:"
BE_QUIET_2 = ":regional_indicator_s: :regional_indicator_h: :regional_indicator_h: :regional_indicator_h: :regional_indicator_h:  {} :bangbang: :sleeping: :sleepy: :zzz: :sleeping_accommodation: :regional_indicator_q: :regional_indicator_u: :regional_indicator_i: :regional_indicator_e: :regional_indicator_t:    :regional_indicator_t: :regional_indicator_i: :regional_indicator_m: :regional_indicator_e: :stopwatch: :alarm_clock: :clock: :regional_indicator_m: :regional_indicator_e: :regional_indicator_a: :regional_indicator_n: :regional_indicator_s: :zipper_mouth: :zipper_mouth: :zipper_mouth: :zipper_mouth: :zipper_mouth: :zipper_mouth: :regional_indicator_q: :regional_indicator_u: :regional_indicator_i: :regional_indicator_e: :regional_indicator_t: :sleeping: :thumbsdown: :no_entry_sign: :thinking: :thinking: :ok_hand:"
BE_QUIET_3 = ":rage: :rage: :rage: {} :sparkling_heart: :sparkling_heart: :regional_indicator_i: :sparkling_heart: :sparkling_heart: won't :loudspeaker: :loudspeaker: :loud_sound: tell :thumbsdown: :broken_heart:  you :no_good: :no_mouth:  again. :rage: :rage: :no_entry_sign:  :regional_indicator_s: :regional_indicator_t: :regional_indicator_f: :regional_indicator_u: :zzz: :regional_indicator_i: :regional_indicator_t: :regional_indicator_s: :sleeping: :sleepy: :zzz: :sleeping_accommodation: :regional_indicator_q: :regional_indicator_u: :regional_indicator_i: :regional_indicator_e: :regional_indicator_t:    :regional_indicator_t: :regional_indicator_i: :regional_indicator_m: :regional_indicator_e: :stopwatch: :alarm_clock: :clock:"

DONE = ":sparkles: :regional_indicator_d: :regional_indicator_o: :regional_indicator_n: :regional_indicator_e:  :sparkles:"

SPACER = ":heavy_plus_sign:  :heavy_plus_sign:"
ENABLED = ":fire: :fire: :regional_indicator_e: :regional_indicator_n: :regional_indicator_a: :regional_indicator_b: :regional_indicator_l: :regional_indicator_e: :regional_indicator_d: :fire: :fire:"
DISABLED = ":mobile_phone_off: :mobile_phone_off: :regional_indicator_d: :regional_indicator_i: :regional_indicator_s: :regional_indicator_a: :regional_indicator_b: :regional_indicator_l: :regional_indicator_e: :regional_indicator_d: :mobile_phone_off: :mobile_phone_off:"
SUPERMOD = ":sparkles: :sparkles: :regional_indicator_s: :regional_indicator_u: :regional_indicator_p: :regional_indicator_e: :regional_indicator_r: :regional_indicator_m: :regional_indicator_o: :regional_indicator_d: :sparkles: :sparkles: :cop:"
THINKING = ":thinking: :thinking: :regional_indicator_n: :regional_indicator_o: :regional_indicator_t: :regional_indicator_h: :regional_indicator_i: :regional_indicator_n: :regional_indicator_k: :regional_indicator_i: :regional_indicator_n: :regional_indicator_g: :thinking: :thinking:"

SUPERMOD_ENABLED = "{} {} {}".format(SUPERMOD, SPACER, ENABLED)
SUPERMOD_DISABLED = "{} {} {}".format(SUPERMOD, SPACER, DISABLED)

THINKING_ENABLED = "{} {} {}".format(THINKING, SPACER, ENABLED)
THINKING_DISABLED = "{} {} {}".format(THINKING, SPACER, DISABLED)

CHANNEL_ENABLED = "{} " + SPACER + " " + ENABLED
CHANNEL_DISABLED = "{} " + SPACER + " " + DISABLED


def char_to_emoji(c):
    c = c.lower()
    if c < 'a' or c > 'z':
        return c

    base = 127462
    adjustment = ord(c) - ord('a')
    return chr(base + adjustment) + ' '


def replace_regional_indicator(s):
    s = s.replace('regional_indicator_', '')
    chunks = re.split('(:\w:)', s)
    result = ''
    for chunk in chunks:
        if len(chunk) == 3 and chunk.startswith(':') and chunk.endswith(':'):
            result += char_to_emoji(chunk.strip(':'))
        else:
            result += chunk
    return result


REFRESH_STARTED = replace_regional_indicator(REFRESH_STARTED)
REFRESH_REMOVED_QUIET = replace_regional_indicator(REFRESH_REMOVED_QUIET)
REFRESH_REMOVED_SUPERMOD = replace_regional_indicator(REFRESH_REMOVED_SUPERMOD)
REFRESH_ADDED_SUPERMOD = replace_regional_indicator(REFRESH_ADDED_SUPERMOD)

USER_RENAME_FAILED_DISABLED = replace_regional_indicator(USER_RENAME_FAILED_DISABLED)
USER_RENAME_SUCCEEDED = replace_regional_indicator(USER_RENAME_SUCCEEDED)
USER_RENAME_CLEARED = replace_regional_indicator(USER_RENAME_CLEARED)
USER_RENAME_FAILED = replace_regional_indicator(USER_RENAME_FAILED)

USER_QUIET_FAILED_DISABLED = replace_regional_indicator(USER_QUIET_FAILED_DISABLED)
USER_QUIET_FAILED_SUPERMOD = replace_regional_indicator(USER_QUIET_FAILED_SUPERMOD)
USER_QUIET_SUCCEEDED = replace_regional_indicator(USER_QUIET_SUCCEEDED)

CHANNEL_RENAME_SUCCEEDED = replace_regional_indicator(CHANNEL_RENAME_SUCCEEDED)
CHANNEL_RENAME_FAILED = replace_regional_indicator(CHANNEL_RENAME_FAILED)

CHANNEL_TOPIC_SUCCEEDED = replace_regional_indicator(CHANNEL_TOPIC_SUCCEEDED)
CHANNEL_TOPIC_FAILED = replace_regional_indicator(CHANNEL_TOPIC_FAILED)

USER_SET_IGNORE = replace_regional_indicator(USER_SET_IGNORE)
USER_CLEARED_IGNORE = replace_regional_indicator(USER_CLEARED_IGNORE)

BE_QUIET_1 = replace_regional_indicator(BE_QUIET_1)
BE_QUIET_2 = replace_regional_indicator(BE_QUIET_2)
BE_QUIET_3 = replace_regional_indicator(BE_QUIET_3)

DONE = replace_regional_indicator(DONE)

SPACER = replace_regional_indicator(SPACER)
ENABLED = replace_regional_indicator(ENABLED)
DISABLED = replace_regional_indicator(DISABLED)
SUPERMOD = replace_regional_indicator(SUPERMOD)
THINKING = replace_regional_indicator(THINKING)

SUPERMOD_ENABLED = replace_regional_indicator(SUPERMOD_ENABLED)
SUPERMOD_DISABLED = replace_regional_indicator(SUPERMOD_DISABLED)

THINKING_ENABLED = replace_regional_indicator(THINKING_ENABLED)
THINKING_DISABLED = replace_regional_indicator(THINKING_DISABLED)

CHANNEL_ENABLED = replace_regional_indicator(CHANNEL_ENABLED)
CHANNEL_DISABLED = replace_regional_indicator(CHANNEL_DISABLED)


SUPERMOD_MESSAGE = ("You have been chosen as {}\n"
                    "```You now have moderation power over discussion channels. You can:\n"
                    "Give someone a nickname:\n\t^supermod rename @user new name\n"
                    "Clear a nickname:\n\t^supermod rename @user\n"
                    "Put someone in quiet time:\n\t^supermod quiet @user\n"
                    "Rename the current discussion channel:\n\t^supermod chat new_channel_name\n"
                    "Change the current discussion topic:\n\t^supermod topic new discussion topic\n"
                    "\n"
                    "Use these powers wisely! If you abuse them you might be blacklisted.\n"
                    "Do something really bad and you might be punished.\n"
                    "\n"
                    "If you don't want to participate, use ^supermod ignoreme to opt-out```").format(SUPERMOD)

DEFAULT_SUPERMOD_COUNT = 5

SUPERMOD_COG = None


def is_supermod_check(ctx):
    server = ctx.message.server
    author = ctx.message.author
    supermod_role = SUPERMOD_COG.get_supermod_role(server)
    if supermod_role is None:
        return False
    else:
        return supermod_role in author.roles


def is_supermod():
    return commands.check(is_supermod_check)


class SuperMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = SuperModSettings("supermod")

        self.server_id_to_last_spoke = defaultdict(dict)
        self.server_id_to_last_no_thinking = defaultdict(dict)

        global SUPERMOD_COG
        SUPERMOD_COG = self

        self.server_id_to_quiet_user_ids = defaultdict(dict)

    async def refresh_supermod(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('SuperMod'):
            try:
                await self.do_refresh_supermod()
            except Exception as e:
                print(e)

            await asyncio.sleep(self.settings.getRefreshTimeSec())

    def text_to_emoji(self, text):
        new_msg = ""
        for char in text:
            if char.isalpha():
                new_msg += ':regional_indicator_{}: '.format(char.lower())
            elif char == ' ':
                new_msg += '   '
            elif char.isspace():
                new_msg += char
        return new_msg

    def get_supermod_role(self, server):
        if not server:
            return
        supermod_role_id = self.settings.getSupermodRole(server.id)
        if supermod_role_id:
            return get_role_from_id(self.bot, server, supermod_role_id)
        else:
            return None

    def check_supermod(self, member: discord.Member, supermod_role: discord.Role):
        return supermod_role in member.roles if supermod_role else False

    async def add_supermod(self, member: discord.Member, supermod_role: discord.Role):
        if supermod_role and not self.check_supermod(member, supermod_role):
            try:
                await self.bot.add_roles(member, supermod_role)
                await self.bot.send_message(member, SUPERMOD_MESSAGE)
            except Exception as e:
                print('Failed to supermod', member.name)
                print(e)

    async def remove_supermod(self, member: discord.Member, supermod_role: discord.Role):
        if supermod_role and self.check_supermod(member, supermod_role):
            try:
                await self.bot.remove_roles(member, supermod_role)
            except Exception as e:
                print("failed to remove supermod", member.name, e)

    def get_current_supermods(self, server: discord.Guild, supermod_role: discord.Role):
        if supermod_role is None:
            return []
        return [member for member in server.members if self.check_supermod(member, supermod_role)]

    def get_user_name(self, server, user_id):
        member = server.get_member(user_id)
        return "{} ({})".format(member.name if member else '<unknown>', user_id)

    def get_channel_name(self, server, channel_id):
        channel = server.get_channel(channel_id)
        return "{} ({})".format(channel.name if channel else '<unknown>', channel_id)

    async def do_modlog(self, server_id, log_text, do_say=True):
        mod_log_channel_id = self.settings.getModlogChannel(server_id)
        if mod_log_channel_id:
            try:
                await self.bot.send_message(discord.Object(mod_log_channel_id), log_text)
            except:
                print("Couldn't log to " + mod_log_channel_id)

        if do_say:
            await self.bot.say(log_text)

    async def do_refresh_supermod(self):
        print('REFRESH STARTING')
        for server_id, server in self.settings.servers().items():
            if not self.settings.serverEnabled(server_id):
                continue

            server = self.bot.get_server(server_id)
            if server is None:
                continue

            supermod_role = self.get_supermod_role(server)
            if supermod_role is None:
                continue

            output = REFRESH_STARTED + "\n"

            permanent_supermods = self.settings.permanentSupermod(server_id)
            for member in self.get_current_supermods(server, supermod_role):
                if member.id in permanent_supermods:
                    continue
                await self.remove_supermod(member, supermod_role)
                output += "\n" + REFRESH_REMOVED_SUPERMOD.format(member.name)

            output = output.strip() + "\n"

            quiet_users = self.server_id_to_quiet_user_ids[server_id].keys()
            for user_id in quiet_users:
                output += "\n" + REFRESH_REMOVED_QUIET.format(member.name)
            self.server_id_to_quiet_user_ids[server_id].clear()

            users_spoken = self.server_id_to_last_spoke[server_id].keys()

            blacklisted_supermods = self.settings.blacklistUsers(server_id)
            ignored_supermods = self.settings.ignoreUsers()

            users_spoken = filter(
                lambda user_id: user_id not in blacklisted_supermods and user_id not in ignored_supermods, users_spoken)
            users_spoken = list(users_spoken)

            supermod_count = self.settings.getSupermodCount(server_id)
            new_mods = random.sample(users_spoken, min(len(users_spoken), supermod_count))
            self.server_id_to_last_spoke[server_id].clear()
            self.server_id_to_last_no_thinking[server_id].clear()

            new_mods += permanent_supermods
            new_mods = set(new_mods)

            output = output.strip() + "\n"

            for new_mod in new_mods:
                member = server.get_member(new_mod)
                if member is None:
                    print('Failed to look up member for id', new_mod)
                    continue

                if self.check_supermod(member, supermod_role):
                    continue

                await self.add_supermod(member, supermod_role)
                output += "\n" + REFRESH_ADDED_SUPERMOD.format(member.name)

            for page in pagify(output):
                await self.do_modlog(server_id, page, do_say=False)

    def should_process_user_message(self, message):
        if not message.server or not message.channel:
            return False

        server_id = message.server.id
        channel_id = message.channel.id

        server_enabled = self.settings.serverEnabled(server_id)
        discussion_channel_ids = self.settings.discussionChannels(server_id)
        if not server_enabled or channel_id not in discussion_channel_ids:
            return False

        user_id = message.author.id
        if user_id == self.bot.user.id:
            return False

        if user_id in self.settings.ignoreUsers():
            return False

        return True

    async def log_message(self, message):
        if not self.should_process_user_message(message):
            return

        user_id = message.author.id
        server_id = message.server.id
        self.server_id_to_last_spoke[server_id][user_id] = datetime.now()

        if user_id in self.server_id_to_quiet_user_ids[server_id]:
            try:
                await self.bot.delete_message(message)
                shh_count = self.server_id_to_quiet_user_ids[server_id][user_id]
                self.server_id_to_quiet_user_ids[server_id][user_id] = shh_count + 1
                if shh_count % 5 != 0:
                    return
                msg = None
                if shh_count < 5:
                    msg = BE_QUIET_1
                elif shh_count < 10:
                    msg = BE_QUIET_2
                elif shh_count < 15:
                    msg = BE_QUIET_3
                if msg:
                    await self.bot.send_message(message.channel, msg.format(message.author.mention))
            except Exception as e:
                print(e)

    async def no_thinking(self, message):
        if not self.should_process_user_message(message):
            return

        server_id = message.server.id
        thinking_enabled = self.settings.thinkingEnabled(server_id)

        if not thinking_enabled:
            return

        contains_native_thinking_emoji = '🤔' in message.clean_content
        banned_emoji_contents = [
            'tha',
            'the',
            'thi',
            'tho',
            'thu',
            'king',
            'kang',
        ]
        bad_msg = False
        for banned in banned_emoji_contents:
            emoji_regex = '.*:.*{}.*:.*'.format(banned)
            if re.match(emoji_regex, message.clean_content.lower()):
                bad_msg = True
                break

        if not bad_msg and not contains_native_thinking_emoji:
            return

        user_id = message.author.id
        if user_id not in self.server_id_to_last_no_thinking[server_id]:
            self.server_id_to_last_no_thinking[server_id][user_id] = datetime.now()
            img_tuple = random.choice(NO_THINKING_IMAGES)
            embed = discord.Embed()
            embed.set_image(url=img_tuple[0])
            embed.set_footer(text=img_tuple[1])
            color = ''.join([random.choice('0123456789ABCDEF') for x in range(6)])
            color = int(color, 16)
            embed.color = discord.Color(value=color)
            await self.bot.send_message(message.channel, embed=embed)

        await self.bot.delete_message(message)

    @commands.group(pass_context=True)
    async def supermod(self, context):
        """Automagical selection of moderators for your server."""
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @supermod.command(pass_context=True)
    @checks.is_owner()
    async def setRefreshTime(self, ctx, refresh_time_sec: int):
        """Set the global refresh period for SuperMod, in seconds (global)."""
        self.settings.setRefreshTimeSec(refresh_time_sec)
        await self.bot.say(DONE)
        await self.bot.say('be sure to reload!')

    @supermod.command(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def toggleServerEnabled(self, ctx):
        """Enables or disables SuperMod on this server."""
        now_enabled = self.settings.toggleServerEnabled(ctx.message.server.id)
        await self.bot.say(SUPERMOD_ENABLED if now_enabled else SUPERMOD_DISABLED)

    @supermod.command(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def toggleThinkingEnabled(self, ctx):
        """Enables or disables :thinking: on this server."""
        now_enabled = self.settings.toggleThinkingEnabled(ctx.message.server.id)
        await self.bot.say(THINKING_ENABLED if now_enabled else THINKING_DISABLED)

    @supermod.command(pass_context=True)
    @checks.is_owner()
    async def forceRefresh(self, ctx):
        """Forces an immediate refresh of the SuperMods."""
        await self.do_refresh_supermod()
        await self.bot.say(DONE)

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def modhelp(self, ctx):
        """Prints help for moderators"""
        for page in pagify(MOD_HELP):
            await self.bot.whisper(box(page))

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def addPermanentSupermod(self, ctx, user: discord.Member):
        """Ensures a user is always selected as SuperMod."""
        self.settings.addPermanentSupermod(ctx.message.server.id, user.id)
        await self.bot.say(DONE)

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def rmPermanentSupermod(self, ctx, user: discord.Member):
        """Removes a user from the always SuperMod list."""
        self.settings.rmPermanentSupermod(ctx.message.server.id, user.id)
        await self.bot.say(DONE)

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def setSupermodCount(self, ctx, count: int):
        """Set the number of automatically selected SuperMods on this server."""
        self.settings.setSupermodCount(ctx.message.server.id, count)
        await self.bot.say(DONE)

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def setModLogChannel(self, ctx, channel: discord.Channel):
        """Sets the channel used for printing moderation logs."""
        self.settings.setModlogChannel(ctx.message.server.id, channel.id)
        await self.bot.say(DONE)

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def clearModLogChannel(self, ctx):
        """Clears the channel used for printing moderation logs."""
        self.settings.clearModlogChannel(ctx.message.server.id)
        await self.bot.say(DONE)

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def setSupermodRole(self, ctx, role_name: str):
        """Sets the role that designates a user as SuperMod (make sure to hoist it)."""
        role = get_role(ctx.message.server.roles, role_name)
        self.settings.setSupermodRole(ctx.message.server.id, role.id)
        await self.bot.say(DONE)

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def clearSupermodRole(self, ctx):
        """Clears the role that designates a user as SuperMod."""
        self.settings.clearSupermodRole(ctx.message.server.id)
        await self.bot.say(DONE)

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def addDiscussionChannel(self, ctx, channel: discord.Channel):
        """Marks a channel as containing discussion.

        Discussion channels are automatically monitored for activity. Users active in these
        channels have a chance of becoming a SuperMod.

        Discussion channels are also eligible for SuperMod activities like renaming and
        topic changing.
        """
        self.settings.addDiscussionChannel(ctx.message.server.id, channel.id)
        msg = CHANNEL_ENABLED.format(self.text_to_emoji(channel.name))
        await self.do_modlog(ctx.message.server.id, msg)

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def rmDiscussionChannel(self, ctx, channel: discord.Channel):
        """Clears the discussion status from a channel."""
        self.settings.rmDiscussionChannel(ctx.message.server.id, channel.id)
        msg = CHANNEL_DISABLED.format(self.text_to_emoji(channel.name))
        await self.do_modlog(ctx.message.server.id, msg)

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def addBlacklistedUser(self, ctx, member: discord.Member):
        """Removes SuperMod status from a user (if they have it) and ensures they won't be selected."""
        self.settings.addBlacklistUser(ctx.message.server.id, member.id)
        await self.do_modlog(ctx.message.server.id, inline('{} was naughty, no SuperMod fun time for them'.format(member.name)))
        await self.remove_supermod(member, self.get_supermod_role(ctx.message.server))

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def rmBlacklistedUser(self, ctx, member: discord.Member):
        """Re-enable SuperMod selection for a user."""
        self.settings.rmBlacklistUser(ctx.message.server.id, member.id)
        await self.do_modlog(ctx.message.server.id, inline('{} was forgiven, they can SuperMod again}'.format(member.name)))

    @supermod.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def info(self, ctx):
        """Print the SuperMod configuration for this server."""
        server = ctx.message.server
        server_id = server.id

        refresh_time_sec = self.settings.getRefreshTimeSec()
        users_spoken = self.server_id_to_last_spoke[server_id]
        server_enabled = self.settings.serverEnabled(server_id)
        thinking_enabled = self.settings.thinkingEnabled(server_id)
        supermod_count = self.settings.getSupermodCount(server_id)
        supermod_role = self.get_supermod_role(server)
        mod_log_channel_id = self.settings.getModlogChannel(server_id)
        discussion_channel_ids = self.settings.discussionChannels(server_id)
        permanent_supermods = self.settings.permanentSupermod(server_id)
        current_supermods = self.get_current_supermods(server, supermod_role)
        blacklisted_supermods = self.settings.blacklistUsers(server_id)
        ignored_supermods = self.settings.ignoreUsers()
        quiet_users = self.server_id_to_quiet_user_ids[server_id]

        supermod_role_output = supermod_role.name if supermod_role else 'Not configured'

        output = 'SuperMod configuration:\n'
        output += '\nrefresh_sec: {}'.format(refresh_time_sec)
        output += '\nusers spoken: {}'.format(len(users_spoken))
        output += '\nsupermod count: {}'.format(supermod_count)
        output += '\nsupermod role: {}'.format(supermod_role_output)
        output += '\nserver enabled: {}'.format(server_enabled)
        output += '\nthinking enabled: {}'.format(thinking_enabled)
        output += '\nmodlog channel: {}'.format(self.get_channel_name(server, mod_log_channel_id))

        output += '\ndiscussion channels:'
        for channel_id in discussion_channel_ids:
            output += '\n\t{}'.format(self.get_channel_name(server, channel_id))

        output += '\npermanent supermods:'
        for user_id in permanent_supermods:
            output += '\n\t{}'.format(self.get_user_name(server, user_id))

        output += '\ncurrent supermods:'
        for member in current_supermods:
            output += '\n\t{}'.format(self.get_user_name(server, member.id))

        output += '\nblacklisted users:'
        for user_id in blacklisted_supermods:
            output += '\n\t{}'.format(self.get_user_name(server, user_id))

        output += '\nignored users:'
        for user_id in ignored_supermods:
            output += '\n\t{}'.format(self.get_user_name(server, user_id))

        output += '\nquiet users:'
        for user_id in quiet_users:
            output += '\n\t{}'.format(self.get_user_name(server, user_id))

        for page in pagify(output):
            await self.bot.say(box(page))

    @supermod.command(pass_context=True)
    async def help(self, ctx):
        """Prints help for users"""
        for page in pagify(USER_HELP):
            await self.bot.whisper(box(page))

    @supermod.command(pass_context=True, no_pm=True)
    @is_supermod()
    async def rename(self, ctx, member: discord.Member, *, new_name: str=None):
        """You're a SuperMod! Set the nickname on a user."""
        if not self.should_process_user_message(ctx.message):
            return

        author_name = ctx.message.author.name
        server_id = ctx.message.server.id

        if member.id in self.settings.ignoreUsers():
            msg = USER_RENAME_FAILED_DISABLED.format(author_name, member.name)
            await self.bot.say(msg)
            return

        member_old_name = member.name
        msg_template = None
        try:
            await self.bot.change_nickname(member, new_name)
            if new_name:
                msg_template = USER_RENAME_SUCCEEDED
            else:
                msg_template = USER_RENAME_SUCCEEDED
        except Exception as e:
            msg_template = USER_RENAME_FAILED

        msg = msg_template.format(author_name, member_old_name, new_name)
        await self.do_modlog(server_id, msg)

    @supermod.command(pass_context=True, no_pm=True)
    @is_supermod()
    async def quiet(self, ctx, member: discord.Member):
        """You're a SuperMod! Put someone in time-out."""
        if not self.should_process_user_message(ctx.message):
            return

        author_name = ctx.message.author.name
        server = ctx.message.server
        server_id = server.id

        if member.id in self.settings.ignoreUsers():
            msg = USER_QUIET_FAILED_DISABLED.format(author_name, member.name)
            await self.bot.say(msg)
            return

        supermod_role = self.get_supermod_role(server)
        if self.check_supermod(member, supermod_role):
            msg = USER_QUIET_FAILED_SUPERMOD.format(author_name, member.name)
            await self.bot.say(msg)
            return

        quiet_users = self.server_id_to_quiet_user_ids[server_id][member.id] = 0
        msg_template = USER_QUIET_SUCCEEDED

        msg = msg_template.format(author_name, member.name)
        await self.do_modlog(server_id, msg)

    @supermod.command(pass_context=True, no_pm=True)
    @is_supermod()
    async def chat(self, ctx, *, new_channel_name):
        """You're a SuperMod! Change the channel name."""
        if not self.should_process_user_message(ctx.message):
            return

        server_id = ctx.message.server.id
        channel = ctx.message.channel
        channel_id = channel.id
        old_channel_name = channel.name
        discussion_channel_ids = self.settings.discussionChannels(server_id)

        msg_template = None
        try:
            await self.bot.edit_channel(channel, name=new_channel_name)
            msg_template = CHANNEL_RENAME_SUCCEEDED
        except Exception as e:
            msg_template = CHANNEL_RENAME_FAILED

        msg = msg_template.format(ctx.message.author.name, old_channel_name, new_channel_name)
        await self.do_modlog(server_id, msg)

    @supermod.command(pass_context=True, no_pm=True)
    @is_supermod()
    async def topic(self, ctx, *, new_channel_topic):
        """You're a SuperMod! Change the channel topic."""
        if not self.should_process_user_message(ctx.message):
            return

        server_id = ctx.message.server.id
        channel = ctx.message.channel
        channel_id = channel.id
        discussion_channel_ids = self.settings.discussionChannels(server_id)

        msg_template = None
        try:
            await self.bot.edit_channel(channel, topic=new_channel_topic)
            msg_template = CHANNEL_TOPIC_SUCCEEDED
        except Exception as e:
            msg_template = CHANNEL_TOPIC_FAILED

        msg = msg_template.format(ctx.message.author.name, channel.name, new_channel_topic)
        await self.do_modlog(ctx.message.server.id, msg)

    @supermod.command(pass_context=True)
    async def ignoreme(self, ctx):
        """I guess you can set this if you don't like SuperMod, but why?"""
        author = ctx.message.author
        self.settings.addIgnoreUser(author.id)
        await self.bot.say(USER_SET_IGNORE.format(author.name))

    @supermod.command(pass_context=True)
    async def noticeme(self, ctx):
        """You do like SuperMod! I knew you'd be back."""
        author = ctx.message.author
        self.settings.rmIgnoreUser(author.id)
        await self.bot.say(USER_CLEARED_IGNORE.format(author.name))


def setup(bot):
    n = SuperMod(bot)
    bot.loop.create_task(n.refresh_supermod())
    bot.add_listener(n.log_message, "on_message")
    bot.add_listener(n.no_thinking, "on_message")
    bot.add_cog(n)


class SuperModSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'refresh_time_sec': 10 * 60,
            'servers': {},
        }
        return config

    def getRefreshTimeSec(self):
        return self.bot_settings['refresh_time_sec']

    def setRefreshTimeSec(self, time_sec):
        self.bot_settings['refresh_time_sec'] = int(time_sec)
        self.save_settings()

    def servers(self):
        key = 'servers'
        if key not in self.bot_settings:
            self.bot_settings[key] = {}
        return self.bot_settings[key]

    def getServer(self, server_id):
        servers = self.servers()
        if server_id not in servers:
            servers[server_id] = {}
        return servers[server_id]

    def permanentSupermod(self, server_id):
        key = 'permanent_supermods'
        server = self.getServer(server_id)
        if key not in server:
            server[key] = []
        return server[key]

    def addPermanentSupermod(self, server_id, user_id):
        supermods = self.permanentSupermod(server_id)
        if user_id not in supermods:
            supermods.append(user_id)
            self.save_settings()

    def rmPermanentSupermod(self, server_id, user_id):
        self.permanentSupermod(server_id).remove(user_id)
        self.save_settings()

    def ignoreUsers(self):
        key = 'ignore_users'
        if key not in self.bot_settings:
            self.bot_settings[key] = []
        return self.bot_settings[key]

    def addIgnoreUser(self, user_id):
        ignore_users = self.ignoreUsers()
        if user_id not in ignore_users:
            ignore_users.append(user_id)
            self.save_settings()

    def rmIgnoreUser(self, user_id):
        ignore_users = self.ignoreUsers()
        if user_id in ignore_users:
            ignore_users.remove(user_id)
            self.save_settings()

    def blacklistUsers(self, server_id):
        server = self.getServer(server_id)
        key = 'blacklist_users'
        if key not in server:
            server[key] = []
        return server[key]

    def addBlacklistUser(self, server_id, user_id):
        blacklist_users = self.blacklistUsers(server_id)
        if user_id not in blacklist_users:
            blacklist_users.append(user_id)
            self.save_settings()

    def rmBlacklistUser(self, server_id, user_id):
        self.blacklistUsers(server_id).remove(user_id)
        self.save_settings()

    def serverEnabled(self, server_id):
        server = self.getServer(server_id)
        return server.get('enabled', False)

    def toggleServerEnabled(self, server_id):
        new_enabled = not self.serverEnabled(server_id)
        self.getServer(server_id)['enabled'] = new_enabled
        self.save_settings()
        return new_enabled

    def thinkingEnabled(self, server_id):
        server = self.getServer(server_id)
        return server.get('thinking_enabled', True)

    def toggleThinkingEnabled(self, server_id):
        new_enabled = not self.thinkingEnabled(server_id)
        self.getServer(server_id)['thinking_enabled'] = new_enabled
        self.save_settings()
        return new_enabled

    def getSupermodCount(self, server_id):
        server = self.getServer(server_id)
        return server.get('supermod_count', DEFAULT_SUPERMOD_COUNT)

    def setSupermodCount(self, server_id, count):
        server = self.getServer(server_id)
        server['supermod_count'] = count
        self.save_settings()

    def getModlogChannel(self, server_id):
        server = self.getServer(server_id)
        return server.get('modlog_channel', None)

    def setModlogChannel(self, server_id, channel_id):
        server = self.getServer(server_id)
        server['modlog_channel'] = channel_id
        self.save_settings()

    def clearModlogChannel(self, server_id):
        server = self.getServer(server_id)
        server.pop('modlog_channel')
        self.save_settings()

    def getSupermodRole(self, server_id):
        server = self.getServer(server_id)
        return server.get('supermod_role', None)

    def setSupermodRole(self, server_id, role_id):
        server = self.getServer(server_id)
        server['supermod_role'] = role_id
        self.save_settings()

    def clearSupermodRole(self, server_id):
        server = self.getServer(server_id)
        server.pop('supermod_role')
        self.save_settings()

    def discussionChannels(self, server_id):
        key = 'discussion_channels'
        server = self.getServer(server_id)
        if key not in server:
            server[key] = []
        return server[key]

    def addDiscussionChannel(self, server_id, channel_id):
        channels = self.discussionChannels(server_id)
        if channel_id not in channels:
            channels.append(channel_id)
            self.save_settings()

    def rmDiscussionChannel(self, server_id, channel_id):
        channels = self.discussionChannels(server_id)
        if channel_id in channels:
            channels.remove(channel_id)
            self.save_settings()


# Too lazy to do something better than this
NO_THINKING_IMAGES = [
    ['https://i.imgur.com/aWNsKEx.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=42706272'],
    ['https://i.imgur.com/EpjyHDB.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=42740222'],
    ['https://i.imgur.com/eixwKYD.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=57134596'],
    ['https://i.imgur.com/8E7RKXB.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=52477807'],
    ['https://i.imgur.com/JUgwbN6.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=52189749'],
    ['https://i.imgur.com/hkbI56M.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=53126204'],
    ['https://i.imgur.com/R7Q2WW8.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=52317589'],
    ['https://i.imgur.com/ECejTVs.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=53369582'],
    ['https://i.imgur.com/yOoxRWe.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=53369582'],
    ['https://i.imgur.com/qqGtxSU.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=53369582'],
    ['https://i.imgur.com/fOuaGAR.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=46132779'],
    ['https://i.imgur.com/1PdRTVm.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=54188744'],
    ['https://i.imgur.com/ssuG3l0.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=54188493'],
    ['https://i.imgur.com/05GnuqM.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=54238502'],
    ['https://i.imgur.com/ITAScDP.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=54203561'],
    ['https://i.imgur.com/XZDu1bt.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=43339714'],
    ['https://i.imgur.com/hWfqoO6.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=54782916'],
    ['https://i.imgur.com/33UWBXW.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=56189276'],
    ['https://i.imgur.com/9YeuYMi.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=57634676'],
    ['https://i.imgur.com/Cy7CeiX.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60259727'],
    ['https://i.imgur.com/SQuXlJw.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60272457'],
    ['https://i.imgur.com/pzssttM.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60475690'],
    ['https://i.imgur.com/Lv8G7ZF.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=59478665'],
    ['https://i.imgur.com/PtxZLx2.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60446325'],
    ['https://i.imgur.com/l55Tlhj.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=54084234'],
    ['https://i.imgur.com/p6OISy7.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60547587'],
    ['https://i.imgur.com/VC7slX4.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60520659'],
    ['https://i.imgur.com/vuN78sT.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60564608'],
    ['https://i.imgur.com/u26Tg3y.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60548661'],
    ['https://i.imgur.com/dOGCddg.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61139758'],
    ['https://i.imgur.com/IfkCta1.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61546669'],
    ['https://i.imgur.com/To6XI2C.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61416100'],
    ['https://i.imgur.com/Fo12qho.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61712176'],
    ['https://i.imgur.com/svIP5aP.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61682639'],
    ['https://i.imgur.com/h9gAZjB.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61657897'],
    ['https://i.imgur.com/GrEM6Lu.jpg', 'rakulog.tumblr.com'],
    ['https://i.imgur.com/xo86V98.png', 'rakulog.tumblr.com'],
    ['https://i.imgur.com/AsraNjf.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60543589'],
    ['https://i.imgur.com/FHhiaRo.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60861839'],
    ['https://i.imgur.com/EXPw2PA.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60394766'],
    ['https://i.imgur.com/5Y0BxbF.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61052848'],
    ['https://i.imgur.com/D6yi0lp.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61709496'],
    ['https://i.imgur.com/keWPRza.jpg', 'https://twitter.com/prprpnpn/status/837365458768519168'],
    ['https://i.imgur.com/poa7pnu.png', 'https://twitter.com/mi_398/status/835462977163702272'],
    ['https://i.imgur.com/MFoHCaL.jpg', 'https://twitter.com/prprpnpn/status/813417956914839552'],
    ['https://i.imgur.com/ouVSTHL.jpg', 'https://twitter.com/nokomakawa/status/812596889258340352'],
    ['https://i.imgur.com/6wGFUdN.jpg', 'https://twitter.com/nokomakawa/status/812596889258340352'],
    ['https://i.imgur.com/6mCdDNh.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=37322771'],
    ['https://i.imgur.com/Bon8dbU.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=37504678'],
    ['https://i.imgur.com/DOlKOqO.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=37504678'],
    ['https://i.imgur.com/uPXosj6.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=37504678'],
    ['https://i.imgur.com/UNPSaIZ.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=37504678'],
    ['https://i.imgur.com/C1KCO3x.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61590223'],
    ['https://i.imgur.com/CNC86kK.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60181682'],
    ['https://i.imgur.com/3vGHERt.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61662355'],
    ['https://i.imgur.com/IKf4wHS.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61662355'],
    ['https://i.imgur.com/aYLKPr9.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61662355'],
    ['https://i.imgur.com/w1S30Dv.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61662355'],
    ['https://i.imgur.com/qYVzxf4.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60002450'],
    ['https://i.imgur.com/sodFqBe.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=59964667'],
    ['https://i.imgur.com/wao0nZB.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60050876'],
    ['https://i.imgur.com/r6dBgMH.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60277218'],
    ['https://i.imgur.com/vQaapOd.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60266091'],
    ['https://i.imgur.com/Jujn0o0.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61711985'],
    ['https://i.imgur.com/aAS3iTA.png', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61593794'],
    ['https://i.imgur.com/jVtFkA4.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=61517564'],
    ['https://i.imgur.com/zixy122.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60178036'],
    ['https://i.imgur.com/19WEnBI.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60049282'],
    ['https://i.imgur.com/yMxoM9s.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60089967'],
    ['https://i.imgur.com/2qi2chk.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=59886432'],
    ['https://i.imgur.com/7XxGqVL.jpg', 'https://twitter.com/pikomarie_pzdr/status/836610799908970499'],
    ['https://i.imgur.com/u2vVQkP.jpg', 'https://twitter.com/tamagoumigeso/status/794140023863947264'],
    ['https://i.imgur.com/VLnOumt.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60244312'],
    ['https://i.imgur.com/g9ouibR.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=59820989'],
    ['https://i.imgur.com/9AlAKWQ.jpg', 'https://twitter.com/0xg3r51r78r049b/status/836451708548993024'],
    ['https://i.imgur.com/q84LZwd.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60019520'],
    ['https://i.imgur.com/5lHArn1.jpg', 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=60129743'],
]
