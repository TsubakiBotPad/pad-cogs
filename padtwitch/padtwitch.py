from __future__ import print_function

import asyncio
from copy import deepcopy
from datetime import datetime
import errno
import os
import re
import socket
import threading
import time

from dateutil import tz
import discord
from redbot.core import commands

from rpadutils.rpadutils import CogSettings
from redbot.core import checks
from redbot.core.utils.chat_formatting import *


if os.name != 'nt':
    import fcntl


class PadTwitch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = PadTwitchSettings("padtwitch")

        user_name = self.settings.getUserName()
        oauth_code = self.settings.getOauthCode()

        self.stream = None
        self.stream_thread = None

        if user_name and oauth_code:
            self.stream = TwitchChatStream(username=user_name, oauth=oauth_code, verbose=False)

        self.monster_actions = {
            '^as ': self.post_as,
            '^info ': self.post_info,
            '^ls ': self.post_ls,
        }

        self.actions = {
            '^help': self.whisper_help,
            '^addcc ': self.add_com,
            '^rmcc ': self.rm_com,
            '^cc': self.whisper_commands,
        }

    def _try_shutdown_twitch(self):
        if self.stream:
            self.stream.disconnect()
        if self.stream_thread:
            print('shutting down stream thread')
            self.stream_thread.join()
            self.stream_thread = None
            print('done shutting down stream thread')

    def __unload(self):
        self._try_shutdown_twitch()

    async def on_connect(self):
        """Called when connected as a Discord client.

        Connects to Twitch IRC.
        """
        self._try_shutdown_twitch()
        self.stream_thread = self.connect_thread()

    def connect_thread(self, *args, **kwargs):
        """Convenient wrapper for calling follow() in a background thread.
        The Thread object is started and then returned. Passes on args and kwargs to
        the follow() method."""
        thread = threading.Thread(target=self.connect_stream, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    def connect_stream(self):
        if self.stream is None:
            print('Not connecting stream, set up username/oauth first')
            return

        self.stream.connect()

        for channel in self.settings.channels().values():
            if channel['enabled']:
                channel_name = channel['name']
                print('Connecting to twitch channel: {}'.format(channel_name))
                self.stream.join_channel(channel_name)

        while True:
            received = self.stream.twitch_receive_messages()
            if received:
                for m in received:
                    self.process_user_message(**m)
                time.sleep(.1)

    def process_user_message(self, message, channel, username):
        for action_name, action_fn in self.monster_actions.items():
            if message.startswith(action_name):
                query = message[len(action_name):]
                m = self.lookup_monster(query)
                msg = action_fn(channel, username, m) if m else 'no matches for ' + query
                self.stream.send_chat_message(channel, msg)
                return

        for action_name, action_fn in self.actions.items():
            if message.startswith(action_name):
                query = message[len(action_name):]
                action_fn(channel, username, query)
                return

        for command_name, command_response in self.settings.getCustomCommands(channel).items():
            if message.rstrip()[1:] == command_name:
                self.stream.send_chat_message(channel, command_response)
                return

    def lookup_monster(self, query):
        padinfo = self.bot.get_cog('PadInfo')
        if not padinfo:
            return None
        m, _, _ = padinfo.findMonster(query)
        return m

    def _get_header(self, m):
        return '{}. {}'.format(m.monster_id_na, m.name_na)

    def post_as(self, channel, username, m):
        as_text = '(CD{}) {}'.format(m.active_skill.turn_min,
                                     m.active_skill.desc) if m.active_skill else 'None/Missing'
        return '{} : {}'.format(self._get_header(m), as_text)

    def post_info(self, channel, username, m):
        name = self._get_header(m)
        types = m.type1 + ('/' + m.type2 if m.type2 else '') + ('/' + m.type3 if m.type3 else '')
        stats = '({}/{}/{}) W{}'.format(m.hp, m.atk, m.rcv, m.weighted_stats)
        awakenings = self.bot.get_cog('PadInfo').map_awakenings_text(m)
        return '{} | {} | {} | {}'.format(name, types, stats, awakenings)

    def post_ls(self, channel, username, m):
        ls_text = "[{}] {}".format(
            m.multiplier_text, m.leader_text) if m.leader_text else 'None/Missing'
        return '{} : {}'.format(self._get_header(m), ls_text)

    def whisper_help(self, channel, username, m):
        help_text = 'Cmds: ^info <q>, ^as <q>, ^ls <q>, ^cc'
        self.stream.send_chat_message(channel, help_text)

    def whisper_commands(self, channel, username, m):
        cmds_with_prefix = map(lambda x: '^' + x, self.settings.getCustomCommands(channel))
        msg = "Custom Cmds: " + ', '.join(cmds_with_prefix)
        self.stream.send_chat_message(channel, msg)

    def add_com(self, channel, username, query):
        query = query.strip()
        if '"' in query or '^' in query or ' ' not in query:
            self.stream.send_chat_message(channel, 'bad request')
            return

        space_idx = query.index(' ')
        cmd_name = query[:space_idx]
        cmd_value = query[space_idx:]
        self.settings.addCustomCommand(channel, cmd_name, cmd_value)
        self.stream.send_chat_message(channel, 'Done adding ' + cmd_name)

    def rm_com(self, channel, username, query):
        cmd_name = query.strip()
        self.settings.rmCustomCommand(channel, cmd_name)
        self.stream.send_chat_message(channel, 'Done deleting ' + cmd_name)

    @commands.group()
    @checks.is_owner()
    async def padtwitch(self, ctx):
        """Manage twitter feed mirroring"""

    @padtwitch.command()
    async def setUserName(self, ctx, user_name: str):
        self.settings.setUserName(user_name)
        await ctx.send(inline('done, reload the cog'))

    @padtwitch.command()
    async def setOauthCode(self, ctx, oauth_code: str):
        self.settings.setOauthCode(oauth_code)
        await ctx.send(inline('done, reload the cog'))

    @padtwitch.command()
    async def setEnabled(self, ctx, twitch_channel: str, enabled: bool):
        self.settings.setChannelEnabled(twitch_channel, enabled)
        await ctx.send(inline('done, reload the cog'))

    @padtwitch.command()
    async def join(self, ctx, twitch_channel):
        self.stream.join_channel(twitch_channel)
        await ctx.send(inline('done'))

    @padtwitch.command()
    async def send(self, ctx, twitch_channel, *, msg_text):
        self.stream.send_chat_message(twitch_channel, msg_text)
        await ctx.send(inline('done'))

    @padtwitch.command()
    async def list(self, ctx):
        msg = 'UserName: {}'.format(self.settings.getUserName())
        msg += '\nChannels:'
        for channel, cs in self.settings.channels().items():
            msg += '\n\t({}) {}'.format('+' if cs['enabled'] else '-', cs['name'])

        await ctx.send(box(msg))


class PadTwitchSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'channels': {},
            'user_name': '',
            'oauth_code': '',
        }
        return config

    def getUserName(self):
        return self.bot_settings['user_name']

    def setUserName(self, user_name):
        self.bot_settings['user_name'] = user_name
        self.save_settings()

    def getOauthCode(self):
        return self.bot_settings['oauth_code']

    def setOauthCode(self, oauth_code):
        self.bot_settings['oauth_code'] = oauth_code
        self.save_settings()

    def channels(self):
        return self.bot_settings['channels']

    def getChannel(self, channel_name):
        channels = self.channels()
        if channel_name not in channels:
            channels[channel_name] = {
                'name': channel_name,
                'enabled': False,
                'custom_commands': {},
            }
        return channels[channel_name]

    def setChannelEnabled(self, channel_name: str, enabled: bool):
        self.getChannel(channel_name)['enabled'] = enabled
        self.save_settings()

    def getCustomCommands(self, channel_name: str):
        return self.getChannel(channel_name)['custom_commands']

    def addCustomCommand(self, channel_name: str, cmd_name: str, cmd_value: str):
        self.getCustomCommands(channel_name)[cmd_name] = cmd_value
        self.save_settings()

    def rmCustomCommand(self, channel_name: str, cmd_name: str):
        self.getCustomCommands(channel_name).pop(cmd_name)
        self.save_settings()


"""
Adapted from:
https://github.com/317070/python-twitch-stream/blob/master/twitchstream/chat.py

This file contains the python code used to interface with the Twitch
chat. Twitch chat is IRC-based, so it is basically an IRC-bot, but with
special features for Twitch, such as congestion control built in.
"""


class TwitchChatStream(object):
    """
    The TwitchChatStream is used for interfacing with the Twitch chat of
    a channel. To use this, an oauth-account (of the user chatting)
    should be created. At the moment of writing, this can be done here:
    https://twitchapps.com/tmi/

    :param username: Twitch username
    :type username: string
    :param oauth: oauth for logging in (see https://twitchapps.com/tmi/)
    :type oauth: string
    :param verbose: show all stream messages on stdout (for debugging)
    :type verbose: boolean
    """

    def __init__(self, username, oauth, verbose=False):
        """Create a new stream object, and try to connect."""
        self.username = username
        self.oauth = oauth
        self.verbose = verbose
        self.current_channel = ""
        self.last_sent_time = time.time()
        self.buffer = []
        self.s = None
        self.in_shutdown = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    @staticmethod
    def _logged_in_successful(data):
        """
        Test the login status from the returned communication of the
        server.

        :param data: bytes received from server during login
        :type data: list of bytes

        :return boolean, True when you are logged in.
        """
        if re.match(r'^:(testserver\.local|tmi\.twitch\.tv)'
                    r' NOTICE \* :'
                    r'(Login unsuccessful|Error logging in)*$',
                    data.strip()):
            return False
        else:
            return True

    @staticmethod
    def _check_has_ping(data):
        """
        Check if the data from the server contains a request to ping.

        :param data: the byte string from the server
        :type data: list of bytes
        :return: True when there is a request to ping, False otherwise
        """
        return re.match(r'^PING :tmi\.twitch\.tv$', data)

    @staticmethod
    def _check_has_channel(data):
        """
        Check if the data from the server contains a channel switch.

        :param data: the byte string from the server
        :type data: list of bytes
        :return: Name of channel when new channel, False otherwise
        """
        return re.findall(
            r'^:[a-zA-Z0-9_]+\![a-zA-Z0-9_]+@[a-zA-Z0-9_]+'
            r'\.tmi\.twitch\.tv '
            r'JOIN #([a-zA-Z0-9_]+)$', data)

    @staticmethod
    def _check_has_message(data):
        """
        Check if the data from the server contains a message a user
        typed in the chat.

        :param data: the byte string from the server
        :type data: list of bytes
        :return: returns iterator over these messages
        """
        return re.match(r'^:[a-zA-Z0-9_]+\![a-zA-Z0-9_]+@[a-zA-Z0-9_]+'
                        r'\.tmi\.twitch\.tv '
                        r'PRIVMSG #[a-zA-Z0-9_]+ :.+$', data)

    def connect(self):
        """
        Connect to Twitch
        """

        if self.s:
            self.disconnect()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s = s
        connect_host = "irc.twitch.tv"
        connect_port = 6667
        try:
            print('starting connect to {} {}'.format(connect_host, connect_port))
            s.connect((connect_host, connect_port))
        except (Exception, IOError):
            print("Unable to create a socket to %s:%s" % (
                connect_host,
                connect_port))
            raise  # unexpected, because it is a blocking socket

        # Connected to twitch
        # Sending our details to twitch...
        self._send_now('PASS %s\r\n' % self.oauth)
        self._send_now('NICK %s\r\n' % self.username)

        received = s.recv(1024).decode()
        if not TwitchChatStream._logged_in_successful(received):
            self.s = None
            # ... and they didn't accept our details
            raise IOError("Twitch did not accept the username-oauth "
                          "combination")

        # ... and they accepted our details
        # Connected to twitch.tv!
        # now make this socket non-blocking on the OS-level
        if os.name != 'nt':
            fcntl.fcntl(s, fcntl.F_SETFL, os.O_NONBLOCK)
        else:
            s.setblocking(0)

        print('done with twitch connect')
        self.in_shutdown = False  # This is bad. probably need to use a connection counter or something

    def disconnect(self):
        if self.s is not None:
            print('doing disconnect')
            self.in_shutdown = True
            self.s.close()  # close the previous socket
            self.s = None
            print('done doing disconnect')

    def _push_from_buffer(self):
        """
        Push a message on the stack to the IRC stream.
        This is necessary to avoid Twitch overflow control.
        """
        if len(self.buffer) > 0:
            if time.time() - self.last_sent_time > 5:
                try:
                    message = self.buffer.pop(0)
                    self._send_now(message)
                finally:
                    self.last_sent_time = time.time()

    def _send_now(self, message: str):
        if not message:
            return

        self._maybe_print('twitch out now: ' + message)

        if self.s is None:
            print('Error: socket was None but tried to send a message')
            return

        self.s.send(message.encode())

    def _send(self, message):
        """
        Send a message to the IRC stream

        :param message: the message to be sent.
        :type message: string
        """
        if not message:
            return

        self._maybe_print('twitch out queued: ' + message)
        self.buffer.append(message + "\n")

    def _send_pong(self):
        """
        Send a pong message, usually in reply to a received ping message
        """
        self._send("PONG")

    def join_channel(self, channel):
        """
        Join a different chat channel on Twitch.
        Note, this function returns immediately, but the switch might
        take a moment

        :param channel: name of the channel (without #)
        """
        self._send('JOIN #%s\r\n' % channel)

    def send_chat_message(self, channel, message):
        """
        Send a chat message to the server.

        :param message: String to send (don't use \\n)
        """
        self._send("PRIVMSG #{0} :{1}".format(channel, message))

    def send_whisper_message(self, channel, user, message):
        """
        Send a chat whisper to the server.

        :param message: String to send (don't use \\n)
        """
        self._send("PRIVMSG #{0} :/w {1} {2}".format(channel, user, message))

    def _parse_message(self, data):
        """
        Parse the bytes received from the socket.

        :param data: the bytes received from the socket
        :return:
        """
        if TwitchChatStream._check_has_ping(data):
            self._maybe_print('got ping')
            self._send_pong()

        channel_name_or_false = TwitchChatStream._check_has_channel(data)
        if channel_name_or_false:
            current_channel = channel_name_or_false[0]
            print('Connected to channel: ' + current_channel)

        if TwitchChatStream._check_has_message(data):
            msg = {
                'channel': re.findall(r'^:.+![a-zA-Z0-9_]+'
                                      r'@[a-zA-Z0-9_]+'
                                      r'.+ '
                                      r'PRIVMSG (.*?) :',
                                      data)[0],
                'username': re.findall(r'^:([a-zA-Z0-9_]+)!', data)[0],
                'message': re.findall(r'PRIVMSG #[a-zA-Z0-9_]+ :(.+)',
                                      data)[0]
            }
            if msg['channel'].startswith('#'):
                msg['channel'] = msg['channel'][1:]
            self._maybe_print(
                'got msg: #{} @{} -- {}'.format(msg['channel'], msg['username'], msg['message']))
            return msg
        elif len(data):
            self._maybe_print('other data: {}'.format(data))
        else:
            return None

    def twitch_receive_messages(self):
        """
        Call this function to process everything received by the socket
        This needs to be called frequently enough (~10s) Twitch logs off
        users not replying to ping commands.

        :return: list of chat messages received. Each message is a dict
            with the keys ['channel', 'username', 'message']
        """
        self._push_from_buffer()
        result = []
        while True:
            # process the complete buffer, until no data is left no more
            try:
                time.sleep(.01)
                if self.s is None:
                    raise Exception('socket is closed')
                msg = self.s.recv(4096).decode()  # NON-BLOCKING RECEIVE!
            except socket.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    # There is no more data available to read
                    if len(result):
                        self._maybe_print('returning with {}'.format(result))

                    return result
                else:
                    # a "real" error occurred
                    # import traceback
                    # import sys
                    # print(traceback.format_exc())
                    if not self.in_shutdown:
                        print("Trying to recover...")
                        self.connect()
                    return result
            else:
                self._maybe_print('twitch in: ' + msg)
                rec = [self._parse_message(line)
                       for line in filter(None, msg.split('\r\n'))]
                rec = [r for r in rec if r]  # remove Nones
                result.extend(rec)
                self._maybe_print("result length {} {}".format(len(result), result))

    def _maybe_print(self, msg: str):
        if self.verbose and msg:
            print(msg)
